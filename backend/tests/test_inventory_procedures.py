"""Real MySQL checks with independent stock/ledger/error expectations."""
import os

import pytest

from app.content.challenges import BY_ID
from app.content.inventory_procedures import TRANSFER_STOCK, RECEIVE_DELIVERY, rollback_probes
from app.engine import (Job, provision, destroy, learner_connection, close_learner,
                        execute, probe, snapshot, control_results, connect, grade)
from app.sql import validate_script

pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL 8.4")]


@pytest.fixture
def receipt_workspace():
    workspace = provision("inventory", 0, "procedure")
    job = Job("inventory-independent", "owner", "BI-P02", "submit")
    connection = learner_connection(workspace, job)
    execute(connection, [TRANSFER_STOCK, RECEIVE_DELIVERY], job)
    try:
        yield workspace, connection, job
    finally:
        close_learner(connection, job)
        destroy(workspace)


def rows(workspace, sql):
    return control_results(workspace, sql)["rows"]


def success(connection, job, sql):
    result = probe(connection, sql, job)
    assert result["error"] is None, result
    assert len(result["results"]) == 1, result
    return result["results"][0]["rows"][0]


def test_transfer_independent_balances_ledger_and_stable_replay(receipt_workspace):
    workspace, connection, job = receipt_workspace
    first = success(connection, job, "CALL transfer_stock('one',1,1,2,5,'2026-06-30')")
    assert first[1:] == [5, "COMPLETED"]
    assert rows(workspace, "SELECT store_id,on_hand,reserved FROM stock WHERE product_id=1 ORDER BY store_id") == [[1,25,5],[2,10,8]]
    assert rows(workspace, "SELECT store_id,product_id,quantity,transfer_id FROM stock_movements WHERE transfer_id IS NOT NULL ORDER BY store_id") == [[1,1,-5,first[0]],[2,1,5,first[0]]]
    success(connection, job, "CALL transfer_stock('two',1,2,1,2,'2026-06-30')")
    before = snapshot(workspace)
    assert success(connection, job, "CALL transfer_stock('one',1,1,2,5,'2026-06-30')") == first
    assert snapshot(workspace) == before
    success(connection, job, "CALL transfer_stock('all',1,1,2,22,'2026-06-30')")
    assert rows(workspace, "SELECT on_hand,reserved FROM stock WHERE store_id=1 AND product_id=1") == [[5,5]]
    before = snapshot(workspace)
    assert probe(connection, "CALL transfer_stock('short',1,1,2,1,'2026-06-30')", job)["error"] == [1644,"INSUFFICIENT_STOCK"]
    assert snapshot(workspace) == before


def test_receipt_independent_totals_stock_and_original_response(receipt_workspace):
    workspace, connection, job = receipt_workspace
    before = snapshot(workspace)
    first = success(connection, job, "CALL receive_delivery(5000,'2026-06-30')")
    assert first == [5000,3,35,"RECEIVED"]
    assert rows(workspace, "SELECT product_id,on_hand,reserved FROM stock WHERE store_id=1 AND product_id IN (5002,5003) ORDER BY product_id") == [[5002,25,2],[5003,40,3]]
    assert rows(workspace, "SELECT delivery_line_id,quantity FROM stock_movements WHERE delivery_line_id IN (5000,5001,5002) ORDER BY delivery_line_id") == [[5000,10],[5001,20],[5002,5]]
    assert rows(workspace, "SELECT status,lines_received,units_received FROM deliveries WHERE delivery_id=5000") == [["RECEIVED",3,35]]
    assert snapshot(workspace)["purchase_order_lines"] == before["purchase_order_lines"]
    success(connection, job, "CALL receive_delivery(5001,'2026-07-03')")
    before = snapshot(workspace)
    assert success(connection, job, "CALL receive_delivery(5000,'2026-06-30')") == first
    assert snapshot(workspace) == before
    # A previously received batch after July 1 still consumes the allowance.
    assert success(connection, job, "CALL receive_delivery(5011,'2026-06-30')") == [5011,1,3,"RECEIVED"]
    before = snapshot(workspace)
    assert probe(connection, "CALL receive_delivery(5015,'2026-06-30')", job)["error"] == [1644,"DELIVERY_LIMIT_EXCEEDED"]
    assert snapshot(workspace) == before


@pytest.mark.parametrize("sql,error", [
    ("CALL transfer_stock(' ',1,1,2,1,'2026-06-30')", "INVALID_ARGUMENT"),
    ("CALL transfer_stock('same',1,1,1,1,'2026-06-30')", "INVALID_ARGUMENT"),
    ("CALL transfer_stock('missing',1,1,3,1,'2026-06-30')", "RECORD_NOT_FOUND"),
    ("CALL transfer_stock('overflow',5000,2,1,1,'2026-06-30')", "STOCK_OVERFLOW"),
    ("CALL receive_delivery(NULL,'2026-06-30')", "INVALID_ARGUMENT"),
    ("CALL receive_delivery(999999,'2026-06-30')", "DELIVERY_NOT_FOUND"),
    ("CALL receive_delivery(5002,'2026-06-30')", None),
    ("CALL receive_delivery(5003,'2026-06-30')", "INVALID_DELIVERY_LINE"),
    ("CALL receive_delivery(5004,'2026-06-30')", "INVALID_DELIVERY_LINE"),
    ("CALL receive_delivery(5005,'2026-06-30')", "STOCK_NOT_FOUND"),
    ("CALL receive_delivery(5006,'2026-06-30')", "INVALID_DELIVERY_STATE"),
    ("CALL receive_delivery(5007,'2026-06-30')", "INVALID_DELIVERY_LINE"),
    ("CALL receive_delivery(5008,'2026-06-30')", "INVALID_DELIVERY_LINE"),
    ("CALL receive_delivery(5009,'2026-06-30')", "STOCK_OVERFLOW"),
    ("CALL receive_delivery(5010,'2026-04-30')", "INVALID_TIMESTAMP"),
    ("CALL receive_delivery(5013,'2026-06-30')", "INVALID_DELIVERY_STATE"),
    ("CALL receive_delivery(5014,'2026-06-30')", "STOCK_OVERFLOW"),
])
def test_precise_validation_errors_leave_every_table_unchanged(receipt_workspace, sql, error):
    workspace, connection, job = receipt_workspace
    if error is None:
        # Spend allowance first, then a duplicate-line batch jointly exceeds it.
        success(connection, job, "CALL receive_delivery(5000,'2026-06-30')")
        success(connection, job, "CALL receive_delivery(5001,'2026-06-30')")
        error = "DELIVERY_LIMIT_EXCEEDED"
    before = snapshot(workspace)
    assert probe(connection, sql, job)["error"] == [1644,error]
    assert snapshot(workspace) == before


@pytest.mark.parametrize("id", ["BI-P01","BI-P02"])
def test_injected_late_failure_rolls_back_all_tables(receipt_workspace, id):
    workspace, connection, job = receipt_workspace
    case = rollback_probes(id)[0]
    with connect(database=workspace.schema) as control, control.cursor() as cursor:
        for sql in case["setup_sql"]:
            cursor.execute(sql)
    before = snapshot(workspace)
    assert probe(connection, case["sql"], job)["error"] == [1644,"INJECTED_FAILURE"]
    assert snapshot(workspace) == before


@pytest.mark.parametrize("id", ["BI-P01","BI-P02"])
def test_reference_passes_public_and_two_hidden_variants(id):
    challenge = BY_ID[id]
    result = grade(challenge, validate_script(challenge["solution"], grading_type="procedure"), Job("full", "owner", id, "submit"))
    assert result["passed"], result


@pytest.mark.parametrize("id", ["BI-P01","BI-P02"])
def test_correct_alternative_ledger_insertion_order_is_accepted(id):
    challenge = BY_ID[id]
    if id == "BI-P01":
        alternate = challenge["solution"].replace(
            "VALUES(p_source_store_id,p_product_id,-p_quantity,p_occurred_at,v_transfer),\n (p_destination_store_id,p_product_id,p_quantity,p_occurred_at,v_transfer)",
            "VALUES(p_destination_store_id,p_product_id,p_quantity,p_occurred_at,v_transfer),\n (p_source_store_id,p_product_id,-p_quantity,p_occurred_at,v_transfer)")
    else:
        alternate = challenge["solution"].replace("ORDER BY dl.delivery_line_id;", "ORDER BY dl.delivery_line_id DESC;")
    assert alternate != challenge["solution"]
    result = grade(challenge, validate_script(alternate, grading_type="procedure"), Job("alternate", "owner", id, "submit"))
    assert result["passed"], result


def test_correct_transfer_accepts_generated_id_gaps_after_rollback():
    challenge = BY_ID["BI-P01"]
    insert = """ INSERT INTO transfers(request_key,product_id,source_store_id,destination_store_id,quantity,occurred_at)
 VALUES(p_request_key,p_product_id,p_source_store_id,p_destination_store_id,p_quantity,p_occurred_at);
 SET v_transfer=LAST_INSERT_ID();
"""
    assert insert in challenge["solution"]
    alternate = challenge["solution"].replace(insert, "")
    alternate = alternate.replace(" IF v_source_on_hand-v_reserved<p_quantity THEN", insert + " IF v_source_on_hand-v_reserved<p_quantity THEN")
    # First grading probe has insufficient availability: its rolled-back insert
    # consumes an AUTO_INCREMENT value. Later successful IDs may differ legally.
    result = grade(challenge, validate_script(alternate, grading_type="procedure"), Job("alternate-gaps", "owner", "BI-P01", "submit"))
    assert result["passed"], result


@pytest.mark.parametrize("id,old,new", [
    ("BI-P01", "START TRANSACTION;", ""),
    ("BI-P02", "START TRANSACTION;", ""),
    ("BI-P01", "v_source_on_hand-v_reserved<p_quantity", "v_source_on_hand<p_quantity"),
    ("BI-P02", "v_status='RECEIVED'", "FALSE"),
    ("BI-P02", "batch.batch_qty>CAST(pol.ordered_qty AS SIGNED)-pol.cancelled_qty-COALESCE(used.used_qty,0)", "FALSE"),
    ("BI-P02", "d.received_at IS NOT NULL AND d.delivery_id<>p_delivery_id", "d.received_at<'2026-07-01' AND d.delivery_id<>p_delivery_id"),
    ("BI-P02", "p_received_at<v_created", "p_received_at<=v_created"),
    ("BI-P01", "p_product_id<=0", "FALSE"),
    ("BI-P01", "p_source_store_id<=0", "FALSE"),
    ("BI-P01", "p_destination_store_id<=0", "FALSE"),
    ("BI-P01", "START TRANSACTION;", "START TRANSACTION; IF p_occurred_at>='2026-07-01' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_TIMESTAMP'; END IF;"),
])
def test_grader_rejects_known_wrong_procedure(id, old, new):
    challenge = BY_ID[id]
    assert old in challenge["solution"]
    wrong = challenge["solution"].replace(old, new)
    result = grade(challenge, validate_script(wrong, grading_type="procedure"), Job("wrong", "owner", id, "submit"))
    assert not result["passed"], result
