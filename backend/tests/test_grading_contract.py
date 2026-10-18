"""Server error diagnostics are part of the published routine contract."""
import os

import pytest

from app.content.challenges import BY_ID
from app.engine import (Job, close_learner, destroy, equal_probe, execute, grade,
                        learner_connection, probe, provision)
from app.sql import validate_script


pytestmark = [pytest.mark.integration, pytest.mark.skipif(
    os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL 8.4")]


def test_same_mysql_error_number_and_message_keep_distinct_sqlstates():
    workspace = provision("inventory", kind="function")
    job = Job("state-diagnostics", "owner", "BI-F01", "submit")
    connection = None
    try:
        connection = learner_connection(workspace, job)
        expected = probe(connection,
            "SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_ARGUMENT'", job)
        actual = probe(connection,
            "SIGNAL SQLSTATE '45001' SET MESSAGE_TEXT='INVALID_ARGUMENT'", job)
        assert expected["error"] == actual["error"] == [1644, "INVALID_ARGUMENT"]
        assert expected["sqlstate"] == "45000"
        assert actual["sqlstate"] == "45001"
        assert not equal_probe(actual, expected)
        # A successful follow-up must not retain the previous failure state.
        success = probe(connection, "SELECT 42 AS answer", job)
        assert success["error"] is None and success["sqlstate"] is None
        assert success["results"][0]["rows"] == [[42]]
    finally:
        close_learner(connection, job)
        destroy(workspace)


@pytest.mark.parametrize("identifier", ["BI-F01", "BI-P01", "BI-P02", "OS-F01"])
def test_wrong_sqlstate_is_rejected_even_when_errno_and_message_match(identifier):
    challenge = BY_ID[identifier]
    wrong = challenge["solution"].replace("SQLSTATE '45000'", "SQLSTATE '45001'")
    assert wrong != challenge["solution"]
    result = grade(challenge, validate_script(wrong, grading_type=challenge["type"]),
                   Job("wrong-state", "owner", identifier, "submit"))
    assert not result["passed"], result
    assert any(not check["passed"] for check in result["checks"]), result


@pytest.mark.parametrize("original,propagated", [("45001", "45000"), ("45000", "45001")])
def test_resignal_compares_the_final_condition_not_the_original_error(original, propagated):
    workspace = provision("inventory", kind="function")
    job = Job("resignal-diagnostics", "owner", "BI-F01", "submit")
    connection = None
    try:
        connection = learner_connection(workspace, job)
        execute(connection, [f"""CREATE PROCEDURE resignal_state() SQL SECURITY INVOKER
        BEGIN
          DECLARE EXIT HANDLER FOR SQLEXCEPTION
            RESIGNAL SQLSTATE '{propagated}' SET MESSAGE_TEXT='FINAL_ERROR';
          SIGNAL SQLSTATE '{original}' SET MESSAGE_TEXT='ORIGINAL_ERROR';
        END"""], job)
        actual = probe(connection, "CALL resignal_state()", job)
        assert actual["error"] == [1644, "FINAL_ERROR"]
        assert actual["sqlstate"] == propagated
        assert equal_probe(actual, {
            "error": [1644, "FINAL_ERROR"], "sqlstate": propagated, "results": []})
    finally:
        close_learner(connection, job)
        destroy(workspace)
