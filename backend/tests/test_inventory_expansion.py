"""Real MySQL checks with independent Python report/calculation oracles."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import os

import pymysql
import pytest

from app.content.challenges import BY_ID
from app.content.inventory_expansion import (
    REPLENISHMENT, RELIABILITY, RECONCILIATION, REORDER_QUANTITY, routine_probes,
)
from app.engine import (
    Job, close_learner, connect, control_results, destroy, execute, grade,
    learner_connection, probe, provision, snapshot,
)
from app.sql import validate_script

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL 8.4")]
CUTOFF = datetime(2026, 7, 1)
JUNE = datetime(2026, 6, 1)
APRIL = datetime(2026, 4, 1)


def inventory_rows(workspace):
    tables = ("stock", "products", "suppliers", "purchase_orders", "purchase_order_lines",
              "deliveries", "delivery_lines", "stock_movements")
    with connect(database=workspace.schema) as connection, connection.cursor(pymysql.cursors.DictCursor) as cursor:
        result = {}
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            result[table] = cursor.fetchall()
        return result


def report_oracles(data):
    orders = {r["purchase_order_id"]: r for r in data["purchase_orders"]}
    deliveries = {r["delivery_id"]: r for r in data["deliveries"]}
    products = {r["product_id"]: r for r in data["products"]}
    receipts = defaultdict(int)
    for line in data["delivery_lines"]:
        delivery = deliveries[line["delivery_id"]]
        if delivery["status"] == "RECEIVED" and delivery["received_at"] is not None and delivery["received_at"] < CUTOFF:
            receipts[line["purchase_order_line_id"]] += line["quantity"]
    inbound = defaultdict(int)
    for line in data["purchase_order_lines"]:
        order = orders[line["purchase_order_id"]]
        if order["created_at"] < CUTOFF:
            inbound[(order["store_id"], line["product_id"])] += max(
                line["ordered_qty"] - line["cancelled_qty"] - receipts[line["purchase_order_line_id"]], 0)
    replenishment = []
    for row in sorted(data["stock"], key=lambda r: (r["store_id"], r["product_id"])):
        key = row["store_id"], row["product_id"]
        available = row["on_hand"] - row["reserved"]
        incoming = inbound[key]
        position = available + incoming
        if position < row["reorder_point"]:
            pack = products[row["product_id"]]["pack_size"]
            shortfall = max(row["target_qty"] - position, 0)
            packs, remainder = divmod(shortfall, pack)
            replenishment.append([*key, available, incoming, position, (packs + bool(remainder)) * pack])
    reliability = []
    for supplier in data["suppliers"]:
        due = [delivery for delivery in data["deliveries"]
               if orders[delivery["purchase_order_id"]]["supplier_id"] == supplier["supplier_id"]
               and delivery["status"] != "CANCELLED" and APRIL <= delivery["promised_at"] < CUTOFF]
        ontime = sum(delivery["received_at"] is not None
                     and delivery["received_at"] <= delivery["promised_at"]
                     and delivery["received_at"] < CUTOFF for delivery in due)
        pct = (Decimal(100) * ontime / len(due)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if due else None
        reliability.append([supplier["supplier_id"], supplier["supplier_name"], len(due), ontime, len(due) - ontime, pct])
    reliability.sort(key=lambda r: (r[5] is None, -r[5] if r[5] is not None else 0, r[0]))
    reconciliation = []
    for stock in sorted(data["stock"], key=lambda r: (r["store_id"], r["product_id"])):
        movements = [m for m in data["stock_movements"]
                     if (m["store_id"], m["product_id"]) == (stock["store_id"], stock["product_id"])]
        balance = sum(m["quantity"] for m in movements if m["occurred_at"] < JUNE)
        minimum = balance
        for movement in sorted((m for m in movements if JUNE <= m["occurred_at"] < CUTOFF),
                               key=lambda m: (m["occurred_at"], m["movement_id"])):
            balance += movement["quantity"]
            minimum = min(minimum, balance)
        difference = stock["on_hand"] - balance
        if difference or minimum < 0:
            reconciliation.append([stock["store_id"], stock["product_id"], balance, stock["on_hand"], difference, minimum])
    return {"BI-Q01": replenishment, "BI-Q02": reliability, "BI-Q03": reconciliation}


@pytest.mark.parametrize("variant", [0, 1, 2])
def test_inventory_reports_match_independent_python_business_rules(variant):
    workspace = provision("inventory", variant, "query")
    try:
        data = inventory_rows(workspace)
        expected = report_oracles(data)
        for identifier, sql in (("BI-Q01", REPLENISHMENT), ("BI-Q02", RELIABILITY), ("BI-Q03", RECONCILIATION)):
            actual = control_results(workspace, sql)
            assert actual["columns"] == BY_ID[identifier]["expected_columns"]
            assert actual["rows"] == expected[identifier], identifier
        # Sentinel cases ensure the oracle did not silently omit key boundaries.
        shifted = 1000 + variant * 100
        assert [3, shifted + 1, -6, 0, -6, 36] in expected["BI-Q01"]
        assert not any(row[:2] == [3, shifted + 2] for row in expected["BI-Q01"])
        assert [3, shifted + 4, 1, 3, 4, 28] in expected["BI-Q01"]
        assert any(row[0] == shifted + 2 and row[2:] == [0, 0, 0, None] for row in expected["BI-Q02"])
        assert next(row[5] for row in expected["BI-Q02"] if row[0] == shifted + 1) == Decimal(("33.33", "66.67", "25.00")[variant])
        assert [3, shifted + 5, 0, 0, 0, -3] in expected["BI-Q03"]
        assert [3, shifted + 10, -4, 0, 4, -4] in expected["BI-Q03"]
        assert [3, shifted + 11, 0, 3, 3, 0] in expected["BI-Q03"]
        assert [1, 1, 30, 30, 0, -5] in expected["BI-Q03"]
        assert not any(row[:2] == [3, shifted + 6] for row in expected["BI-Q03"])
        assert not any(row[:2] == [3, shifted + 9] for row in expected["BI-Q03"])
    finally:
        destroy(workspace)


ALTERNATIVES = {
    "BI-Q01": """WITH positions AS (
        SELECT s.*,p.pack_size,s.on_hand-s.reserved AS available_qty,
          COALESCE((SELECT SUM(GREATEST(l.ordered_qty-l.cancelled_qty-COALESCE((
            SELECT SUM(dl.quantity) FROM delivery_lines dl JOIN deliveries d ON d.delivery_id=dl.delivery_id
            WHERE dl.purchase_order_line_id=l.purchase_order_line_id AND d.status='RECEIVED'
              AND d.received_at<'2026-07-01'),0),0))
          FROM purchase_order_lines l JOIN purchase_orders po ON po.purchase_order_id=l.purchase_order_id
          WHERE po.store_id=s.store_id AND l.product_id=s.product_id AND po.created_at<'2026-07-01'),0) AS inbound_qty
        FROM stock s JOIN products p ON p.product_id=s.product_id)
        SELECT store_id,product_id,available_qty,inbound_qty,available_qty+inbound_qty AS inventory_position,
          CEIL(GREATEST(target_qty-available_qty-inbound_qty,0)/pack_size)*pack_size AS suggested_order_qty
        FROM positions WHERE available_qty+inbound_qty<reorder_point ORDER BY store_id,product_id""",
    "BI-Q02": """SELECT s.supplier_id,s.supplier_name,COUNT(d.delivery_id) AS deliveries_due,
        SUM(CASE WHEN d.received_at<=d.promised_at AND d.received_at<'2026-07-01' THEN 1 ELSE 0 END) AS on_time_deliveries,
        COUNT(d.delivery_id)-SUM(CASE WHEN d.received_at<=d.promised_at AND d.received_at<'2026-07-01' THEN 1 ELSE 0 END) AS late_or_unreceived,
        ROUND(100.0*SUM(CASE WHEN d.received_at<=d.promised_at AND d.received_at<'2026-07-01' THEN 1 ELSE 0 END)/NULLIF(COUNT(d.delivery_id),0),2) AS on_time_pct
        FROM suppliers s LEFT JOIN purchase_orders po ON po.supplier_id=s.supplier_id
        LEFT JOIN deliveries d ON d.purchase_order_id=po.purchase_order_id AND d.status<>'CANCELLED'
          AND d.promised_at>='2026-04-01' AND d.promised_at<'2026-07-01'
        GROUP BY s.supplier_id,s.supplier_name ORDER BY on_time_pct DESC,s.supplier_id""",
    "BI-Q03": """WITH opening AS (
        SELECT s.*,COALESCE((SELECT SUM(m.quantity) FROM stock_movements m WHERE m.store_id=s.store_id
          AND m.product_id=s.product_id AND m.occurred_at<'2026-06-01'),0) AS opening_qty FROM stock s
        ), balances AS (
        SELECT o.store_id,o.product_id,o.on_hand AS snapshot_qty,
          COALESCE((SELECT SUM(m.quantity) FROM stock_movements m WHERE m.store_id=o.store_id
            AND m.product_id=o.product_id AND m.occurred_at<'2026-07-01'),0) AS ledger_closing_qty,
          LEAST(o.opening_qty,COALESCE((SELECT MIN(o.opening_qty+(
            SELECT SUM(m2.quantity) FROM stock_movements m2 WHERE m2.store_id=m.store_id AND m2.product_id=m.product_id
              AND m2.occurred_at>='2026-06-01' AND (m2.occurred_at<m.occurred_at OR
                (m2.occurred_at=m.occurred_at AND m2.movement_id<=m.movement_id))))
            FROM stock_movements m WHERE m.store_id=o.store_id AND m.product_id=o.product_id
              AND m.occurred_at>='2026-06-01' AND m.occurred_at<'2026-07-01'),o.opening_qty)) AS minimum_balance
        FROM opening o)
        SELECT store_id,product_id,ledger_closing_qty,snapshot_qty,snapshot_qty-ledger_closing_qty AS difference_qty,minimum_balance
        FROM balances WHERE ledger_closing_qty<>snapshot_qty OR minimum_balance<0 ORDER BY store_id,product_id""",
}


@pytest.mark.parametrize("identifier", ["BI-Q01", "BI-Q02", "BI-Q03"])
def test_alternative_correct_inventory_reports_grade_successfully(identifier):
    result = grade(BY_ID[identifier], validate_script(ALTERNATIVES[identifier], grading_type="query"),
                   Job("inventory-alternative", "owner", identifier, "submit"))
    assert result["passed"], result


@pytest.mark.parametrize("identifier,wrong", [
    ("BI-Q01", REPLENISHMENT.replace("s.on_hand-s.reserved", "s.on_hand")),
    ("BI-Q01", REPLENISHMENT.replace("inventory_position < reorder_point", "inventory_position <= reorder_point")),
    ("BI-Q01", REPLENISHMENT.replace("d.received_at < '2026-07-01'", "d.received_at <= '2026-07-01'")),
    ("BI-Q01", REPLENISHMENT.replace("po.created_at < '2026-07-01'", "po.created_at <= '2026-07-01'")),
    ("BI-Q01", REPLENISHMENT.replace(
        "SUM(GREATEST(pol.ordered_qty-pol.cancelled_qty-COALESCE(r.received_qty,0),0))",
        "GREATEST(SUM(pol.ordered_qty-pol.cancelled_qty-COALESCE(r.received_qty,0)),0)")),
    ("BI-Q02", RELIABILITY.replace("d.received_at <= d.promised_at", "d.received_at < d.promised_at")),
    ("BI-Q02", RELIABILITY.replace("d.status <> 'CANCELLED'", "d.status = 'RECEIVED'")),
    ("BI-Q03", RECONCILIATION.replace("ORDER BY m.occurred_at,m.movement_id\n               ROWS", "ORDER BY m.occurred_at\n               RANGE")),
    ("BI-Q03", RECONCILIATION.replace("m.occurred_at < '2026-07-01'", "m.occurred_at <= '2026-07-01'")),
])
def test_plausible_inventory_report_errors_fail(identifier, wrong):
    result = grade(BY_ID[identifier], validate_script(wrong, grading_type="query"),
                   Job("inventory-wrong", "owner", identifier, "submit"))
    assert not result["passed"], result


def reorder_oracle(values):
    if (any(v is None for v in values) or any(v < 0 for v in values[:5])
            or values[5] <= 0 or values[4] < values[3]):
        raise ValueError("INVALID_ARGUMENT")
    hand, reserved, inbound, point, target, pack = values
    position = hand - reserved + inbound
    if position >= point:
        return 0
    count, remainder = divmod(max(target - position, 0), pack)
    return (count + bool(remainder)) * pack


def test_pure_replenishment_matches_independent_python_and_preserves_tables():
    workspace = provision("inventory", kind="function")
    job = Job("reorder-oracle", "owner", "BI-F01", "run")
    connection = None
    try:
        connection = learner_connection(workspace, job)
        execute(connection, validate_script(REORDER_QUANTITY, grading_type="function"), job)
        before = snapshot(workspace)
        for sql, label in routine_probes("BI-F01", 0):
            args = sql.split("(", 1)[1].split(")", 1)[0].split(",")
            values = tuple(None if v == "NULL" else int(v) for v in args)
            actual = probe(connection, sql, job)
            try:
                expected = reorder_oracle(values)
            except ValueError:
                assert actual["error"] == [1644, "INVALID_ARGUMENT"], (label, actual)
            else:
                assert actual["error"] is None, (label, actual)
                assert actual["results"][0]["columns"] == ["reorder_quantity"]
                assert actual["results"][0]["rows"] == [[expected]], (label, actual, expected)
        assert snapshot(workspace) == before
    finally:
        close_learner(connection, job)
        destroy(workspace)


def test_correct_big_decimal_function_alternative_passes_and_low_precision_ceiling_fails():
    integer_result = "RETURN ((v_shortfall+p_pack_size-1) DIV p_pack_size)*p_pack_size;"
    alternative = REORDER_QUANTITY.replace(integer_result,
        "RETURN CEIL(CAST(v_shortfall AS DECIMAL(30,12))/p_pack_size)*p_pack_size;")
    wrong = REORDER_QUANTITY.replace(integer_result, "RETURN CEIL(v_shortfall/p_pack_size)*p_pack_size;")
    for sql, passed in ((alternative, True), (wrong, False)):
        result = grade(BY_ID["BI-F01"], validate_script(sql, grading_type="function"),
                       Job("reorder-alternative", "owner", "BI-F01", "submit"))
        assert result["passed"] is passed, result


@pytest.mark.parametrize("identifier", ["BI-Q01", "BI-Q02", "BI-Q03", "BI-F01"])
def test_inventory_reference_definitions_grade_successfully(identifier):
    challenge = BY_ID[identifier]
    result = grade(challenge, validate_script(challenge["solution"], grading_type=challenge["type"]),
                   Job("inventory-reference", "owner", identifier, "submit"))
    assert result["passed"], result
