from decimal import Decimal
import pytest

from app.sql import split_script,validate_script,SQLPolicyError,same_result
from app.content.solutions import ISSUE_REFUND,LOYALTY_TIER


@pytest.mark.parametrize("delimiter",["$$","//"])
def test_complete_procedures_with_delimiters(delimiter):
    script=f"DELIMITER {delimiter}\n{ISSUE_REFUND}{delimiter}\nDELIMITER ;\nCALL issue_refund('example',1,1,1,'2026-06-30');"
    statements=split_script(script)
    assert len(statements)==2
    assert statements[0].endswith("END")
    assert statements[1].startswith("CALL")


def test_delimiter_text_in_strings_and_comments():
    statements=split_script("DELIMITER //\nCREATE PROCEDURE p() BEGIN SELECT 'https://example.test/'; -- // literal\nSELECT 2; END//\nDELIMITER ;")
    assert len(statements)==1
    assert "https://example.test/" in statements[0]


def test_routines_without_client_delimiter():
    assert len(split_script(ISSUE_REFUND))==1
    assert len(split_script(LOYALTY_TIER))==1
    assert len(validate_script(ISSUE_REFUND,grading_type="procedure"))==1


def test_multiple_statements_and_quoted_semicolon():
    assert split_script("SELECT 'a;b'; SELECT 2;")==["SELECT 'a;b'","SELECT 2"]


@pytest.mark.parametrize("sql",["SELECT SLEEP(5)","SELECT /* hello */ BENCHMARK(100,1)","SELECT * FROM `mysql`.`user`", "SELECT LOAD_FILE('/etc/passwd')", "/*!50000 SELECT SLEEP(1) */", "CREATE DEFINER='root'@'%' PROCEDURE p() SELECT 1", "SET GLOBAL max_connections=100"])
def test_policy_restricts_unsafe_primitives(sql):
    with pytest.raises(SQLPolicyError):validate_script(sql)


def test_denied_words_in_literals_are_not_operations():
    validate_script("SELECT 'mysql sleep definer' AS note")


def test_submit_rejects_fixture_mutation():
    with pytest.raises(SQLPolicyError):validate_script("DELETE FROM customers; SELECT 1",grading_type="query")
    with pytest.raises(SQLPolicyError):validate_script("UPDATE customers SET customer_name='x'",grading_type="function")


def test_comparator_preserves_aliases_order_duplicates_and_decimal_values():
    expected={"columns":["amount"],"rows":[[Decimal("2.00")],[Decimal("2.00")],[None]]}
    assert same_result({"columns":["amount"],"rows":[[2],[2],[None]]},expected)
    assert not same_result({"columns":["amount"],"rows":[[2],[None],[2]]},expected)
    assert not same_result({"columns":["other"],"rows":expected["rows"]},expected)
