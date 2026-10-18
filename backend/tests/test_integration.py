"""Real MySQL integration checks, never substitute sqlite or fabricated results.

Run with QUERYLAB_INTEGRATION=1 and MYSQL_* pointing at a dedicated test DB.
These tests create/drop only their own random ql_ schemas/users. They do not run
Engine.startup, so they may run beside a local API without erasing its sessions.
"""
import os
import secrets
import threading
import time
import pytest
import pymysql

from app.content.challenges import BY_ID
from app.content.solutions import INACTIVE_CUSTOMERS
from app.engine import Engine, EngineError, Job, connect, provision, destroy, grade, learner_connection, execute, close_learner, control_results
from app.sql import validate_script

pytestmark=[pytest.mark.integration,pytest.mark.skipif(os.getenv("QUERYLAB_INTEGRATION")!="1",reason="Set QUERYLAB_INTEGRATION=1 with real MySQL 8.4")]


@pytest.mark.parametrize("id",["OS-Q01","OS-F01","OS-P01"])
def test_reference_solution_passes_all_variants(id):
    challenge=BY_ID[id]
    result=grade(challenge,validate_script(challenge["solution"],grading_type=challenge["type"]),Job("test","owner",id,"submit"))
    assert result["passed"],result


def test_alternative_correct_query_passes():
    sql="""SELECT c.customer_id,c.customer_name,
    (SELECT SUM(i.quantity*i.unit_price - COALESCE((SELECT SUM(r.amount) FROM refunds r WHERE r.order_item_id=i.order_item_id AND r.status='POSTED' AND r.refunded_at<'2026-07-01'),0))
     FROM orders o JOIN order_items i ON i.order_id=o.order_id WHERE o.customer_id=c.customer_id AND o.status='COMPLETED' AND o.completed_at<'2026-07-01') AS net_spending,
    (SELECT MAX(o.completed_at) FROM orders o WHERE o.customer_id=c.customer_id AND o.status='COMPLETED' AND o.completed_at<'2026-07-01') AS last_completed_order_at
    FROM customers c
    HAVING net_spending>=500 AND last_completed_order_at<'2026-04-02'
    ORDER BY net_spending DESC,customer_id"""
    result=grade(BY_ID["OS-Q01"],validate_script(sql,grading_type="query"),Job("alternative","owner","OS-Q01","submit"))
    assert result["passed"],result


def test_wrong_refund_aggregation_fails():
    wrong=INACTIVE_CUSTOMERS.replace("SUM(oi.quantity*oi.unit_price-COALESCE(r.amount,0))","SUM(oi.quantity*oi.unit_price)")
    result=grade(BY_ID["OS-Q01"],validate_script(wrong,grading_type="query"),Job("wrong","owner","OS-Q01","submit"))
    assert not result["passed"]


def test_hardcoded_visible_answer_fails_unseen_fixtures():
    workspace=provision("online-store",kind="query")
    try:rows=control_results(workspace,INACTIVE_CUSTOMERS)["rows"]
    finally:destroy(workspace)
    def literal(value):return "'"+str(value).replace("'","''")+"'"
    selects=[]
    for id,name,spend,completed in rows:
        selects.append(f"SELECT {id} AS customer_id,{literal(name)} AS customer_name,CAST({literal(spend)} AS DECIMAL(12,2)) AS net_spending,CAST({literal(completed)} AS DATETIME) AS last_completed_order_at")
    sql=" UNION ALL ".join(selects)+" ORDER BY net_spending DESC,customer_id"
    result=grade(BY_ID["OS-Q01"],validate_script(sql,grading_type="query"),Job("hardcoded","owner","OS-Q01","submit"))
    assert result["checks"][0]["passed"],result
    assert not result["passed"]


def test_nontransactional_refund_fails_injected_failure():
    challenge=BY_ID["OS-P01"]
    wrong=challenge["solution"].replace("START TRANSACTION;","")
    result=grade(challenge,validate_script(wrong,grading_type="procedure"),Job("no-transaction","owner","OS-P01","submit"))
    injected=[c for c in result["checks"] if c["name"]=="Unexpected database failure"]
    assert len(injected)==3 and all(not c["passed"] for c in injected),result
    assert not result["passed"]


def test_oversized_procedure_mutations_fail_bounded_grading_and_recover():
    engine=Engine()
    session,_=engine.session(create=True)
    challenge=BY_ID["OS-P01"]
    # Otherwise correct first response forces the grader to compare data. The
    # authored fixture has 8 customers; 1000 added rows exceed its snapshot cap.
    oversized=challenge["solution"].replace("START TRANSACTION;","""START TRANSACTION;
    INSERT INTO customers(customer_id,customer_name)
    WITH RECURSIVE n AS (SELECT 1 AS i UNION ALL SELECT i+1 FROM n WHERE i<1000)
    SELECT 10000+i,REPEAT('x',100) FROM n;""")
    try:
        queued=engine.queue(session,challenge,oversized,"submit")
        rejected=wait_job(engine,session,queued["job_id"])
        assert rejected.status=="completed",rejected.view()
        assert not rejected.result["grading"]["passed"]
        assert any(c["name"]=="Fixture integrity" for c in rejected.result["grading"]["checks"]),rejected.view()
        deadline=time.monotonic()+2
        while session.busy and time.monotonic()<deadline:time.sleep(.01)
        following=engine.queue(session,BY_ID["OS-Q01"],"SELECT 42 AS answer","run")
        completed=wait_job(engine,session,following["job_id"])
        assert completed.status=="completed",completed.view()
        assert completed.result["result_sets"][0]["rows"]==[[42]]
    finally:engine.shutdown()


def test_readonly_function_account_cannot_mutate_data():
    workspace=provision("online-store",kind="function")
    job=Job("readonly","owner","OS-F01","run")
    connection=None
    try:
        connection=learner_connection(workspace,job)
        with pytest.raises(pymysql.MySQLError):execute(connection,["UPDATE customers SET customer_name='wrong'"],job)
    finally:
        close_learner(connection,job)
        destroy(workspace)


def test_database_grants_prevent_cross_workspace_access():
    first=provision("online-store")
    second=provision("online-store")
    job=Job("isolation","owner","OS-Q01","run")
    connection=None
    try:
        connection=learner_connection(first,job)
        with pytest.raises(pymysql.MySQLError):execute(connection,[f"SELECT * FROM `{second.schema}`.customers"],job)
        with pytest.raises(pymysql.MySQLError):execute(connection,["SELECT * FROM mysql.user"],job)
        # MySQL returns NULL, rather than an error, without global FILE access.
        assert execute(connection,["SELECT LOAD_FILE('/etc/passwd')"],job)[0]["rows"]==[[None]]
    finally:
        close_learner(connection,job)
        destroy(first)
        destroy(second)


def test_bounded_results_stop_server_work():
    workspace=provision("online-store")
    job=Job("bounds","owner","OS-Q01","run")
    connection=None
    try:
        connection=learner_connection(workspace,job)
        results=execute(connection,["WITH RECURSIVE n AS (SELECT 1 AS i UNION ALL SELECT i+1 FROM n WHERE i<600) SELECT i FROM n"],job)
        assert results[0]["truncated"]
        assert len(results[0]["rows"])==500
    finally:
        close_learner(connection,job)
        destroy(workspace)


@pytest.mark.parametrize("sql",[
    "SELECT REPEAT('x',1100000) AS too_wide",
    "WITH RECURSIVE n AS (SELECT 1 AS i UNION ALL SELECT i+1 FROM n WHERE i<300) SELECT REPEAT('x',10000) AS wide_value FROM n",
    "SELECT REPEAT('x',600000) AS first_payload; SELECT REPEAT('y',600000) AS second_payload",
    "SELECT "+",".join(f"1 AS c{i}" for i in range(257)),
])
def test_result_byte_and_column_caps_allow_subsequent_execution(sql):
    engine=Engine()
    session,_=engine.session(create=True)
    try:
        queued=engine.queue(session,BY_ID["OS-Q01"],sql,"run")
        result=wait_job(engine,session,queued["job_id"])
        assert result.status=="failed",result.view()
        assert result.error["code"]=="result_limit",result.view()
        deadline=time.monotonic()+2
        while session.busy and time.monotonic()<deadline:time.sleep(.01)
        following=engine.queue(session,BY_ID["OS-Q01"],"SELECT 42 AS answer","run")
        completed=wait_job(engine,session,following["job_id"])
        assert completed.status=="completed",completed.view()
        assert completed.result["result_sets"][0]["rows"]==[[42]]
    finally:engine.shutdown()


def wait_job(engine,session,id,seconds=20):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        job=engine.own_job(session,id)
        if job.status not in {"queued","running"}:return job
        time.sleep(.025)
    raise AssertionError("Job did not terminate")


def test_cancel_kills_actual_database_connection_and_releases_workspace():
    engine=Engine()
    session,_=engine.session(create=True)
    try:
        setup=engine.queue(session,BY_ID["OS-Q01"],"CREATE PROCEDURE qa_wait() BEGIN DECLARE x BIGINT DEFAULT 0; WHILE x>=0 DO SET x=x+1; END WHILE; END","run")
        assert wait_job(engine,session,setup["job_id"]).status=="completed"
        queued=engine.queue(session,BY_ID["OS-Q01"],"CALL qa_wait()","run")
        job=engine.own_job(session,queued["job_id"])
        deadline=time.monotonic()+3
        while job.connection_id is None and time.monotonic()<deadline:time.sleep(.01)
        assert job.connection_id is not None
        connection_id=job.connection_id
        job.stop()
        assert wait_job(engine,session,job.id).status=="cancelled"
        deadline=time.monotonic()+2
        while session.busy and time.monotonic()<deadline:time.sleep(.01)
        assert not session.busy
        with connect() as control,control.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM information_schema.PROCESSLIST WHERE ID=%s",(connection_id,))
            assert cursor.fetchone()[0]==0
    finally:engine.shutdown()


def test_run_mutations_survive_submit_and_reset_rotates_credentials():
    engine=Engine()
    session,_=engine.session(create=True)
    try:
        run=engine.queue(session,BY_ID["OS-Q01"],"UPDATE customers SET customer_name='Changed' WHERE customer_id=1","run")
        assert wait_job(engine,session,run["job_id"]).status=="completed"
        old=engine.workspace(session,"online-store")
        submit=engine.queue(session,BY_ID["OS-Q01"],BY_ID["OS-Q01"]["solution"],"submit")
        assert wait_job(engine,session,submit["job_id"]).result["grading"]["passed"]
        assert control_results(old,"SELECT customer_name FROM customers WHERE customer_id=1")["rows"]==[["Changed"]]
        engine.reset(session,"online-store")
        new=engine.workspace(session,"online-store")
        assert old.user!=new.user and old.schema!=new.schema
        assert control_results(new,"SELECT customer_name FROM customers WHERE customer_id=1")["rows"]==[["Maya Chen"]]
        with pytest.raises(pymysql.MySQLError):connect(user=old.user,password=old.password,database=old.schema)
    finally:engine.shutdown()


def test_expiry_reaps_workspace_credentials_and_finished_jobs():
    engine=Engine()
    session,_=engine.session(create=True)
    workspace=engine.workspace(session,"online-store")
    engine.jobs["expired"]=Job("expired",session.token,"OS-Q01","run",status="completed")
    session.expires=time.time()-1
    try:
        engine.reap_once()
        assert session.token not in engine.sessions and "expired" not in engine.jobs
        with pytest.raises(EngineError):engine.session(session.token)
        with pytest.raises(pymysql.MySQLError):connect(user=workspace.user,password=workspace.password,database=workspace.schema)
        with connect() as control,control.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s",(workspace.schema,))
            assert cursor.fetchone()[0]==0
    finally:engine.shutdown()


def test_helper_lifecycle_preserves_unrelated_and_other_namespace_objects(monkeypatch):
    """Real SQL verifies startup, reset and shutdown are installation-scoped."""
    namespace=secrets.token_hex(6)
    other_namespace=secrets.token_hex(6)
    monkeypatch.setenv("QUERYLAB_HELPER_MODE","true")
    monkeypatch.setenv("QUERYLAB_WORKSPACE_NAMESPACE",namespace)
    suffix=secrets.token_hex(12)
    preserved=["sentinel_"+suffix,"ql_"+suffix,f"ql_{other_namespace}_{suffix}"]
    users=["qlu_"+suffix,f"qlu_{other_namespace}_{secrets.token_hex(6)}"]
    orphan_schema=f"ql_{namespace}_{suffix}"
    orphan_user=f"qlu_{namespace}_{secrets.token_hex(6)}"
    current=Engine()
    def assert_preserved():
        with connect() as connection,connection.cursor() as cursor:
            for schema in preserved:
                cursor.execute(f"SELECT marker FROM `{schema}`.sentinel")
                assert cursor.fetchone()==("preserve-me",)
            for user in users:
                cursor.execute("SELECT COUNT(*) FROM mysql.user WHERE User=%s AND Host='%%'",(user,))
                assert cursor.fetchone()[0]==1
    try:
        with connect() as connection,connection.cursor() as cursor:
            for schema in preserved+[orphan_schema]:
                cursor.execute(f"CREATE DATABASE `{schema}`")
                cursor.execute(f"CREATE TABLE `{schema}`.sentinel(marker VARCHAR(32))")
                cursor.execute(f"INSERT INTO `{schema}`.sentinel VALUES('preserve-me')")
            for user in users+[orphan_user]:
                cursor.execute("CREATE USER %s@'%%' IDENTIFIED BY %s",(user,secrets.token_urlsafe(32)))
        current.startup()
        assert_preserved()
        with connect() as connection,connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME=%s",(orphan_schema,))
            assert cursor.fetchone()[0]==0
            cursor.execute("SELECT COUNT(*) FROM mysql.user WHERE User=%s",(orphan_user,))
            assert cursor.fetchone()[0]==0
        session,_=current.session(create=True)
        workspace=current.workspace(session,"online-store")
        assert workspace.schema.startswith(f"ql_{namespace}_") and len(workspace.user)<=32
        current.reset(session,"online-store")
        assert_preserved()
        current.check_database() # readiness retries must not delete live workspaces
        live=current.workspace(session,"online-store")
        assert control_results(live,"SELECT COUNT(*) AS total FROM customers")["rows"][0][0]>0
        current.shutdown()
        assert_preserved()
    finally:
        current.shutdown()
        with connect() as connection,connection.cursor() as cursor:
            # Explicit random identifiers created by this test only.
            for schema in preserved+[orphan_schema]:cursor.execute(f"DROP DATABASE IF EXISTS `{schema}`")
            for user in users+[orphan_user]:cursor.execute("DROP USER IF EXISTS %s@'%%'",(user,))
