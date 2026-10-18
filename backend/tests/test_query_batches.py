"""Optional read-query separators and actionable clause-boundary errors."""
import os

import pytest

from app.sql import SQLPolicyError, split_script, validate_script


@pytest.mark.parametrize("script,count", [
    ("SELECT 1\nSELECT 2", 2),
    ("select 1\r\n  select 2\r\nselect 3", 3),
    ("SELECT 1; SELECT 2", 2),
    ("SELECT\n  1 AS n\nFROM (\n SELECT 2\n) nested\nSELECT 3", 2),
    ("WITH a AS (\nSELECT 1 AS n\n)\nSELECT n FROM a\nSELECT 3", 2),
    ("WITH a AS (SELECT 1 AS n), b AS (SELECT n FROM a)\nSELECT n FROM b", 1),
    ("WITH a AS (SELECT 1 AS n) SELECT n FROM a\nWITH b AS (SELECT 2 AS n) SELECT n FROM b", 2),
    ("SELECT 1\nUNION ALL\nSELECT 2\nSELECT 3", 2),
    ("SELECT 1\nUNION\nDISTINCT\nSELECT 2", 1),
    ("SELECT 1\nINTERSECT\nSELECT 1\nEXCEPT\nSELECT 2", 1),
    ("SELECT 1\nUNION ALL\n(SELECT 2)\nSELECT 3", 2),
    ("SELECT category_id, SUM(quantity) FROM order_items GROUP BY category_id\nWITH ROLLUP", 1),
    ("SELECT 'first\nSELECT not_a_query; second' AS note\nSELECT 2", 2),
    ("-- SELECT ignored\nSELECT 1\n/* SELECT ignored\nSELECT ignored */\nSELECT 2", 2),
    ("SELECT 1 -- trailing comment\nSELECT 2 # another comment\nSELECT 3", 3),
    ("SELECT `SELECT` FROM products\nSELECT 2", 2),
    ("INSERT INTO customers SELECT 1, 'Name'\nSELECT 2", 1),
    ("WITH a AS (SELECT 1 AS n) UPDATE customers SET customer_name='Name'\nSELECT 2", 1),
    ("WITH a AS (SELECT 1 AS n) DELETE FROM customers\nSELECT 2", 1),
    ("CREATE PROCEDURE p() BEGIN\nSELECT 1;\nSELECT 2;\nEND", 1),
    ("SELECT 1 SELECT 2", 1),
])
def test_only_unambiguous_top_level_read_queries_are_split(script, count):
    assert len(split_script(script)) == count


def test_newline_split_preserves_nested_ctes_and_query_text():
    first = "WITH a AS (\n SELECT 1 AS n\n), b AS (\n SELECT n FROM a\n)\nSELECT * FROM b"
    second = "SELECT\n (SELECT 2) AS n"
    assert split_script(first + "\n\n" + second) == [first, second]


@pytest.mark.parametrize("clause", ["GROUP BY order_id", "ORDER BY order_id", "WHERE order_id=1", "HAVING COUNT(*)>1", "LIMIT 10", "INNER JOIN orders USING(order_id)"])
def test_misplaced_semicolon_explains_detached_clause_before_any_execution(clause):
    with pytest.raises(SQLPolicyError, match="Remove the semicolon before"):
        validate_script("SELECT order_id, COUNT(*) FROM order_items;\n" + clause)


def test_optional_separators_still_enforce_one_query_submission_and_statement_limit():
    with pytest.raises(SQLPolicyError, match="Submit one SELECT"):
        validate_script("SELECT 1\nSELECT 2", grading_type="query")
    with pytest.raises(SQLPolicyError, match="at most 30 statements"):
        split_script("\n".join(f"SELECT {n}" for n in range(31)))


@pytest.mark.integration
@pytest.mark.skipif(os.getenv("QUERYLAB_INTEGRATION") != "1", reason="Requires real MySQL 8.4")
def test_optional_separators_execute_separate_results_without_changing_mysql_rules():
    from app.engine import Job, close_learner, destroy, execute, learner_connection, provision
    workspace = provision("online-store")
    job = Job("optional-separators", "owner", "OS-Q01", "run")
    connection = None
    try:
        connection = learner_connection(workspace, job)
        script = """SELECT 42 AS answer
WITH first_cte AS (SELECT 7 AS n)
SELECT n FROM first_cte
SELECT 1 AS n
UNION ALL
SELECT 2 AS n
SELECT 'literal; SELECT inside string' AS note"""
        rows = execute(connection, validate_script(script), job)
        assert [result["rows"] for result in rows] == [[[42]], [[7]], [[1], [2]], [["literal; SELECT inside string"]]]
        grouped = """SELECT srcorders.order_id,
SUM(srcorder_items.quantity * srcorder_items.unit_price) AS total
FROM orders srcorders INNER JOIN order_items srcorder_items
ON srcorders.order_id = srcorder_items.order_id
WHERE srcorders.status = 'Completed'
GROUP BY srcorders.order_id"""
        correct = execute(connection, validate_script(grouped), job)
        assert correct[0]["columns"] == ["order_id", "total"]
        assert len(correct[0]["rows"]) > 1
        rollup = execute(connection, validate_script(
            "SELECT category_id, SUM(quantity) AS quantity FROM order_items GROUP BY category_id\nWITH ROLLUP"), job)
        assert any(row[0] is None for row in rollup[0]["rows"])
        bad = grouped.replace("'Completed'\n", "'Completed';\n")
        with pytest.raises(SQLPolicyError, match="semicolon before GROUP BY"):
            validate_script(bad)
        mode = execute(connection, ["SELECT @@SESSION.sql_mode AS mode"], job)
        assert "ONLY_FULL_GROUP_BY" in mode[0]["rows"][0][0]
    finally:
        close_learner(connection, job)
        destroy(workspace)
