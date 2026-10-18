"""Independent expected values and real-MySQL grading checks for new online exercises."""
import os
from decimal import Decimal, ROUND_HALF_UP

import pymysql
import pytest

from app.content.challenges import BY_ID
from app.content.online_expansion import MONTHLY_NET_SALES, LEADING_PRODUCTS, CUSTOMER_NET_SPEND
from app.engine import (Job, close_learner, connect, control_results, destroy, execute,
                        grade, learner_connection, provision, snapshot)
from app.sql import validate_script


def test_online_content_is_complete():
    for id in ("OS-Q02", "OS-Q03", "OS-F02"):
        challenge = BY_ID[id]
        assert challenge["ready"] and challenge["version"] == "1.1.0"
        assert len(challenge["hints"]) == 3
        assert challenge["expected_columns"] and challenge["solution"] and challenge["explanation"]
        assert "being authored" not in challenge["starter_sql"]


def assess(id, sql):
    challenge = BY_ID[id]
    return grade(challenge, validate_script(sql, grading_type=challenge["type"]),
                 Job("online-check", "owner", id, "submit"))


@pytest.mark.parametrize("id", ["OS-Q02", "OS-Q03", "OS-F02"])
@pytest.mark.integration
@pytest.mark.skipif(os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL")
def test_online_reference_passes_independent_fixtures(id):
    result = assess(id, BY_ID[id]["solution"])
    assert result["passed"], result


@pytest.mark.parametrize("variant", [0, 1, 2])
@pytest.mark.integration
@pytest.mark.skipif(os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL")
def test_monthly_values_against_independent_decimal_oracle(variant):
    workspace = provision("online-store", variant, kind="query")
    try:
        result = control_results(workspace, MONTHLY_NET_SALES)
        assert result["columns"] == BY_ID["OS-Q02"]["expected_columns"]
        # Authored by month, independently of the reference SQL's joins/windows.
        sales = [Decimal(575+25*variant), Decimal(1800), Decimal(900),
                 Decimal(1100), Decimal(0), Decimal(1530+56*variant)]
        running = Decimal(0)
        for month, (row, amount) in enumerate(zip(result["rows"], sales), 1):
            running += amount
            previous = sales[month-2] if month > 1 else None
            growth = None if not previous else ((amount-previous)/previous*100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP)
            assert row[0].isoformat() == f"2026-{month:02d}-01"
            assert Decimal(row[1]) == amount
            assert Decimal(row[2]) == running
            assert (None if row[3] is None else Decimal(row[3])) == growth
        assert len(result["rows"]) == 6
    finally:
        destroy(workspace)


@pytest.mark.parametrize("variant", [0, 1, 2])
@pytest.mark.integration
@pytest.mark.skipif(os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL")
def test_product_ties_and_sale_time_category_against_independent_values(variant):
    workspace = provision("online-store", variant, kind="query")
    try:
        result = control_results(workspace, LEADING_PRODUCTS)
        assert result["columns"] == BY_ID["OS-Q03"]["expected_columns"]
        expected = [(1, 1, 650+17*variant, 1), (1, 5, 650+17*variant, 1),
                    (1, 2, 520+11*variant, 2), (1, 6, 520+11*variant, 2),
                    (2, 9, 90, 1), (3, 4, 50, 1)]
        assert [(r[0], r[1], Decimal(r[3]), r[4]) for r in result["rows"]] == expected
        assert result["rows"][0][2] == result["rows"][1][2] == "Workshop kit"
    finally:
        destroy(workspace)


@pytest.mark.parametrize("variant", [0, 1, 2])
@pytest.mark.integration
@pytest.mark.skipif(os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL")
def test_historical_spend_against_independent_values_errors_and_unchanged_data(variant):
    workspace = provision("online-store", variant, kind="function")
    job = Job("function-oracle", "owner", "OS-F02", "submit")
    connection = None
    try:
        connection = learner_connection(workspace, job)
        execute(connection, [CUSTOMER_NET_SPEND], job)
        before = snapshot(workspace)
        shift = variant*100
        def value(customer, cutoff):
            return Decimal(control_results(workspace,
                f"SELECT customer_net_spend({customer},'{cutoff}') AS customer_net_spend")["rows"][0][0])
        expected = [975+25*variant, 500, 2330+56*variant, 600, 400, 600, 500, 0]
        assert [value(i+shift, "2026-07-01") for i in range(1, 9)] == expected
        for cutoff, amount in [
            ("2026-01-10 10:00:00", 0), ("2026-01-10 10:00:01", 750+25*variant),
            ("2026-01-20 10:00:00", 750+25*variant), ("2026-01-20 10:00:01", 650+25*variant),
            ("2026-02-01 10:00:00", 650+25*variant), ("2026-02-10 10:00:01", 575+25*variant),
            ("2026-07-03", 1075+25*variant)]:
            assert value(1+shift, cutoff) == amount
        assert value(6+shift, "2026-07-01 00:00:01") == 1400
        with connect(database=workspace.schema) as admin, admin.cursor() as cursor:
            for arguments, message in [
                ("NULL,'2026-07-01'", "INVALID_ARGUMENT"),
                (f"{1+shift},NULL", "INVALID_ARGUMENT"),
                ("999999,NULL", "INVALID_ARGUMENT"),
                ("999999,'2026-07-01'", "CUSTOMER_NOT_FOUND")]:
                with pytest.raises(pymysql.MySQLError) as error:
                    cursor.execute(f"SELECT customer_net_spend({arguments})")
                assert error.value.args == (1644, message)
        assert snapshot(workspace) == before
    finally:
        close_learner(connection, job)
        destroy(workspace)


ALTERNATIVE_MONTHLY = """WITH months AS (
 SELECT c.month_start,COALESCE((
  SELECT SUM(i.quantity*i.unit_price-COALESCE((SELECT SUM(r.amount) FROM refunds r
   WHERE r.order_item_id=i.order_item_id AND r.status='POSTED' AND r.refunded_at<'2026-07-01'),0))
  FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.status='COMPLETED'
  AND o.completed_at>=c.month_start AND o.completed_at<DATE_ADD(c.month_start,INTERVAL 1 MONTH)
 ),0) AS net_sales FROM calendar_months c
 WHERE c.month_start>='2026-01-01' AND c.month_start<'2026-07-01'
)
SELECT a.month_start,a.net_sales,
 (SELECT SUM(b.net_sales) FROM months b WHERE b.month_start<=a.month_start) AS running_net_sales,
 ROUND((a.net_sales-p.net_sales)/NULLIF(p.net_sales,0)*100,2) AS month_over_month_pct
FROM months a LEFT JOIN months p ON p.month_start=DATE_SUB(a.month_start,INTERVAL 1 MONTH)
ORDER BY a.month_start"""

ALTERNATIVE_PRODUCTS = """WITH totals AS (
 SELECT i.category_id,i.product_id,SUM(i.quantity*i.unit_price-COALESCE((
 SELECT SUM(r.amount) FROM refunds r WHERE r.order_item_id=i.order_item_id
 AND r.status='POSTED' AND r.refunded_at<'2026-07-01'),0)) AS net_sales
 FROM order_items i JOIN orders o ON o.order_id=i.order_id
 WHERE o.status='COMPLETED' AND o.completed_at>='2026-04-01' AND o.completed_at<'2026-07-01'
 GROUP BY i.category_id,i.product_id
), ranked AS (
 SELECT t.*,1+(SELECT COUNT(DISTINCT higher.net_sales) FROM totals higher
 WHERE higher.category_id=t.category_id AND higher.net_sales>t.net_sales) AS revenue_rank
 FROM totals t WHERE t.net_sales>0
)
SELECT r.category_id,r.product_id,p.product_name,r.net_sales,r.revenue_rank
FROM ranked r JOIN products p ON p.product_id=r.product_id WHERE revenue_rank<=2
ORDER BY category_id,revenue_rank,product_id"""

ALTERNATIVE_FUNCTION = """CREATE FUNCTION customer_net_spend(p_customer_id BIGINT,p_cutoff DATETIME)
RETURNS DECIMAL(12,2) READS SQL DATA SQL SECURITY INVOKER
BEGIN
 DECLARE sales DECIMAL(12,2); DECLARE returned DECIMAL(12,2);
 IF p_customer_id IS NULL OR p_cutoff IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_ARGUMENT'; END IF;
 IF (SELECT COUNT(*) FROM customers WHERE customer_id=p_customer_id)=0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='CUSTOMER_NOT_FOUND'; END IF;
 SELECT COALESCE(SUM(i.quantity*i.unit_price),0) INTO sales FROM orders o JOIN order_items i ON o.order_id=i.order_id
 WHERE o.customer_id=p_customer_id AND o.status='COMPLETED' AND o.completed_at<p_cutoff;
 SELECT COALESCE(SUM(r.amount),0) INTO returned FROM refunds r JOIN order_items i ON i.order_item_id=r.order_item_id
 JOIN orders o ON o.order_id=i.order_id WHERE o.customer_id=p_customer_id AND o.status='COMPLETED'
 AND o.completed_at<p_cutoff AND r.status='POSTED' AND r.refunded_at<p_cutoff;
 RETURN sales-returned;
END"""


@pytest.mark.parametrize("id,sql", [("OS-Q02", ALTERNATIVE_MONTHLY),
    ("OS-Q03", ALTERNATIVE_PRODUCTS), ("OS-F02", ALTERNATIVE_FUNCTION)])
@pytest.mark.integration
@pytest.mark.skipif(os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL")
def test_alternative_correct_online_approaches_pass(id, sql):
    result = assess(id, sql)
    assert result["passed"], result


@pytest.mark.parametrize("id,sql", [
    ("OS-Q02", MONTHLY_NET_SALES.replace("c LEFT JOIN monthly_sales", "c JOIN monthly_sales")),
    ("OS-Q02", MONTHLY_NET_SALES.replace("refunded_at<'2026-07-01'", "refunded_at<='2026-07-01'")),
    ("OS-Q02", MONTHLY_NET_SALES.replace("NULLIF(previous_net_sales,0)", "COALESCE(NULLIF(previous_net_sales,0),1)")),
    ("OS-Q03", LEADING_PRODUCTS.replace("DENSE_RANK()", "ROW_NUMBER()")),
    ("OS-Q03", LEADING_PRODUCTS.replace("DENSE_RANK()", "RANK()")),
    ("OS-Q03", LEADING_PRODUCTS.replace("ORDER BY net_sales DESC)", "ORDER BY net_sales DESC,product_id)")),
    ("OS-Q03", LEADING_PRODUCTS.replace("HAVING SUM(i.quantity*i.unit_price-COALESCE(r.refunded,0))>0", "")),
    ("OS-F02", CUSTOMER_NET_SPEND.replace("refunded_at<p_cutoff", "refunded_at<'2026-07-01'").replace("completed_at<p_cutoff", "completed_at<'2026-07-01'")),
    ("OS-F02", CUSTOMER_NET_SPEND.replace("SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='CUSTOMER_NOT_FOUND';", "RETURN 0.00;")),
    ("OS-F02", CUSTOMER_NET_SPEND.replace("refunded_at<p_cutoff", "refunded_at<=p_cutoff").replace("completed_at<p_cutoff", "completed_at<=p_cutoff")),
])
@pytest.mark.integration
@pytest.mark.skipif(os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL")
def test_incorrect_online_solutions_are_rejected(id, sql):
    result = assess(id, sql)
    assert not result["passed"], result


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL")
def test_hardcoded_visible_monthly_totals_fail_unseen_variants():
    workspace = provision("online-store", kind="query")
    try:
        rows = control_results(workspace, MONTHLY_NET_SALES)["rows"]
    finally:
        destroy(workspace)
    sql = " UNION ALL ".join(
        f"SELECT CAST('{date}' AS DATE) AS month_start,{net} AS net_sales,{running} AS running_net_sales,"
        f"{growth if growth is not None else 'NULL'} AS month_over_month_pct"
        for date, net, running, growth in rows) + " ORDER BY month_start"
    result = assess("OS-Q02", sql)
    assert result["checks"][0]["passed"], result
    assert not result["passed"], result
