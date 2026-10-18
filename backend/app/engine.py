"""Single-process anonymous workspace engine backed by real MySQL 8.4.

Do not run multiple API workers: sessions, quotas and job ownership are in memory.
No submitted SQL ever runs with control-plane credentials.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
import logging
import json
import os
import re
import secrets
import threading
import time
import uuid

import pymysql
from pymysql.cursors import SSCursor

from .content.datasets import DATASETS
from .content.challenges import BY_ID
from .content import online_expansion, inventory_expansion, inventory_procedures
from .sql import json_value, same_result, validate_script, SQLPolicyError

log = logging.getLogger("querylab")
TTL = int(os.getenv("QUERYLAB_SESSION_TTL_SECONDS", "3600"))
MAX_SESSIONS = int(os.getenv("QUERYLAB_MAX_SESSIONS", "10"))
TIMEOUT = int(os.getenv("QUERYLAB_SQL_TIMEOUT_SECONDS", "8"))
MAX_ROWS = 500
MAX_RESULT_BYTES = 1024 * 1024
MAX_RESULT_COLUMNS = 256
MAX_SNAPSHOT_ROWS = 1000
MAX_SNAPSHOT_BYTES = 1024 * 1024
INFRASTRUCTURE_ERRORS = {1040,1045,1203,2002,2003,2006,2013}
SQL_MODE = "STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION,ONLY_FULL_GROUP_BY"


def workspace_namespace():
    namespace = os.getenv("QUERYLAB_WORKSPACE_NAMESPACE", "dev")
    helper = os.getenv("QUERYLAB_HELPER_MODE", "false").lower() == "true"
    if not (re.fullmatch(r"[0-9a-f]{12}", namespace) or (namespace == "dev" and not helper)):
        raise RuntimeError("Set QUERYLAB_WORKSPACE_NAMESPACE to a persistent, unique 12-character lowercase hexadecimal value.")
    return namespace


def owned_identifier(name, *, user=False):
    prefix = "qlu" if user else "ql"
    length = 12 if user else 24
    return bool(re.fullmatch(rf"{prefix}_{workspace_namespace()}_[0-9a-f]{{{length}}}", name))


def validate_server(cursor):
    """Check compatibility before any database/user creation or deletion."""
    cursor.execute("SELECT VERSION(), @@max_allowed_packet, @@log_bin, @@log_bin_trust_function_creators")
    version, packet, binary_log, trust_functions = cursor.fetchone()
    if not re.match(r"^8\.4\.\d+(?:[-+.]|$)", version) or "mariadb" in version.lower():
        raise EngineError("database_version", "QueryLab requires MySQL 8.4.x. Configure MYSQL_HOST and MYSQL_PORT to use a supported server.", 503)
    if int(packet) > 4 * 1024 * 1024:
        raise EngineError("database_configuration", "Set max_allowed_packet=4M in your MySQL configuration and restart MySQL. QueryLab does not change global server settings.", 503)
    if binary_log and not trust_functions:
        raise EngineError("database_configuration", "Routine challenges need log_bin_trust_function_creators=ON when binary logging is enabled. Configure your practice server and restart MySQL.", 503)
    return version


class EngineError(Exception):
    def __init__(self, code, message, status=400):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


class FixtureLimit(Exception):
    """A learner routine changed more fixture data than grading can inspect."""


def connect(*, user=None, password=None, database=None, streaming=False):
    return pymysql.connect(host=os.getenv("MYSQL_HOST", "127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=user or os.getenv("MYSQL_ROOT_USER", "root"),
        password=password if password is not None else os.getenv("MYSQL_ROOT_PASSWORD", ""),
        database=database, charset="utf8mb4", autocommit=True,
        init_command=f"SET SESSION sql_mode='{SQL_MODE}', time_zone='+00:00'",
        connect_timeout=3, read_timeout=TIMEOUT+3, write_timeout=3,
        cursorclass=SSCursor if streaming else pymysql.cursors.Cursor)


@dataclass
class Workspace:
    schema: str
    user: str
    password: str
    dataset: str


@dataclass
class Session:
    token: str
    expires: float
    workspaces: dict = field(default_factory=dict)
    busy: bool = False


@dataclass
class Job:
    id: str
    owner: str
    challenge_id: str
    mode: str
    status: str = "queued"
    result: dict | None = None
    error: dict | None = None
    cancelled: threading.Event = field(default_factory=threading.Event)
    connection_id: int | None = None
    connection_lock: threading.Lock = field(default_factory=threading.Lock)
    timed_out: bool = False
    created: float = field(default_factory=time.time)

    def stop(self, *, timeout=False):
        with self.connection_lock:
            self.timed_out = self.timed_out or timeout
            self.cancelled.set()
            if self.connection_id is not None:
                try:
                    with connect() as control, control.cursor() as cursor:
                        cursor.execute(f"KILL CONNECTION {int(self.connection_id)}")
                except pymysql.MySQLError:
                    log.warning("Could not kill SQL connection", extra={"job_id":self.id})

    def check(self):
        if self.cancelled.is_set():
            raise EngineError("execution_timeout" if self.timed_out else "cancelled",
                              f"Execution exceeded {TIMEOUT} seconds and was stopped." if self.timed_out else "Execution was cancelled.")

    def view(self):
        return dict(job_id=self.id,status=self.status,result=self.result,error=self.error)


def provision(dataset, variant=0, kind="practice"):
    suffix = secrets.token_hex(12)
    namespace = workspace_namespace()
    workspace = Workspace(f"ql_{namespace}_{suffix}", f"qlu_{namespace}_{secrets.token_hex(6)}", secrets.token_urlsafe(32),dataset)
    try:
        with connect() as control, control.cursor() as cursor:
            validate_server(cursor)
            cursor.execute(f"CREATE DATABASE `{workspace.schema}` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci")
            cursor.execute(f"USE `{workspace.schema}`")
            for ddl in DATASETS[dataset]["ddl"]:
                cursor.execute(ddl+" ENGINE=InnoDB")
            DATASETS[dataset]["seed"](cursor,variant)
            cursor.execute("CREATE USER %s@'%%' IDENTIFIED BY %s WITH MAX_USER_CONNECTIONS 2",(workspace.user,workspace.password))
            grants = "SELECT"
            if kind != "query":
                grants += ",CREATE ROUTINE,ALTER ROUTINE,EXECUTE"
            if kind in {"practice","procedure"}:
                grants += ",INSERT,UPDATE,DELETE"
            cursor.execute(f"GRANT {grants} ON `{workspace.schema}`.* TO %s@'%%'",(workspace.user,))
        return workspace
    except Exception:
        destroy(workspace)
        raise


def destroy(workspace):
    if not owned_identifier(workspace.schema) or not owned_identifier(workspace.user,user=True):
        raise EngineError("workspace_scope", "Refusing to remove objects outside this QueryLab installation's namespace.", 403)
    try:
        with connect() as control, control.cursor() as cursor:
            validate_server(cursor)
            cursor.execute(f"DROP DATABASE IF EXISTS `{workspace.schema}`")
            cursor.execute("DROP USER IF EXISTS %s@'%%'",(workspace.user,))
    except pymysql.MySQLError:
        log.exception("Workspace cleanup failed", extra={"schema":workspace.schema})


def learner_connection(workspace, job):
    job.check()
    connection = connect(user=workspace.user,password=workspace.password,database=workspace.schema,streaming=True)
    with job.connection_lock:
        job.connection_id = connection.thread_id()
    job.check()
    with connection.cursor() as cursor:
        cursor.execute("SET SESSION max_execution_time = %s",(TIMEOUT*1000,))
        cursor.execute("SET SESSION innodb_lock_wait_timeout = 3")
        cursor.execute("SET SESSION time_zone = '+00:00'")
    return connection


def abort_result(connection,cursor):
    """Kill work and close without SSCursor draining an unbounded response."""
    try:
        with connect() as control, control.cursor() as killer:
            killer.execute(f"KILL CONNECTION {int(connection.thread_id())}")
    finally:
        # PyMySQL 1.1.1's normal close drains unread rows. This connection must
        # never be reused, so deactivate that drain before closing its socket.
        if cursor._result:
            cursor._result.unbuffered_active=False
            cursor._result.has_next=False
        cursor.connection=None
        connection._force_close()


def execute(connection, statements, job, *, max_rows=MAX_ROWS):
    results = []
    result_bytes=0
    for statement in statements:
        job.check()
        with connection.cursor() as cursor:
            cursor.execute(statement)
            while True:
                if cursor.description:
                    columns = [c[0] for c in cursor.description]
                    if len(columns)>MAX_RESULT_COLUMNS:
                        abort_result(connection,cursor)
                        raise EngineError("result_limit",f"Results are limited to {MAX_RESULT_COLUMNS} columns. Select fewer columns and run again.")
                    result_bytes+=len(json.dumps(columns,ensure_ascii=False).encode("utf-8"))+128
                    rows=[]
                    truncated=False
                    while True:
                        job.check()
                        # Read a single row rather than buffering 500 potentially
                        # wide rows. Deployment also limits MySQL's packet size
                        # to 4 MiB, which bounds the individual protocol row.
                        row=cursor.fetchone()
                        if row is None:break
                        if len(rows)>=max_rows:
                            truncated=True
                            break
                        row=list(row)
                        result_bytes+=len(json.dumps([json_value(v) for v in row],ensure_ascii=False,separators=(",",":")).encode("utf-8"))+1
                        if result_bytes>MAX_RESULT_BYTES:
                            abort_result(connection,cursor)
                            raise EngineError("result_limit","Result data exceeds the 1 MiB response limit. Select fewer columns or rows and run again.")
                        rows.append(row)
                    results.append(dict(columns=columns,rows=rows,truncated=truncated,affected_rows=0))
                    if truncated:
                        # Stop at the server, rather than draining an unbounded
                        # response into memory. Do not execute later statements.
                        abort_result(connection,cursor)
                        return results
                elif cursor.rowcount > 0:
                    results.append(dict(columns=[],rows=[],truncated=False,affected_rows=cursor.rowcount))
                if len(results)>=10:
                    raise EngineError("result_limit","A script may return at most 10 result sets.")
                if not cursor.nextset():
                    break
    return results


def close_learner(connection, job):
    with job.connection_lock:
        job.connection_id = None
    if connection is not None:
        connection.close()


def control_results(workspace, sql):
    # Only authored SQL reaches this helper. Never pass learner SQL here.
    with connect(database=workspace.schema) as control, control.cursor() as cursor:
        cursor.execute(sql)
        return dict(columns=[c[0] for c in cursor.description],rows=[list(row) for row in cursor.fetchall()])


def snapshot(workspace):
    state = {}
    total_bytes=0
    # Never derive a control-plane query identifier from learner-supplied SQL or
    # database objects. These names come only from the authored dataset DDL.
    tables=[re.match(r"CREATE TABLE (\w+)",ddl).group(1) for ddl in DATASETS[workspace.dataset]["ddl"]]
    with connect(database=workspace.schema,streaming=True) as control, control.cursor() as cursor:
        for table in tables:
            cursor.execute(f"SELECT * FROM `{table}`")
            rows=[]
            while True:
                row=cursor.fetchone()
                if row is None:break
                row=tuple(json_value(v) for v in row)
                total_bytes+=len(json.dumps(row,ensure_ascii=False,separators=(",",":")).encode("utf-8"))+1
                if len(rows)>=MAX_SNAPSHOT_ROWS or total_bytes>MAX_SNAPSHOT_BYTES:
                    abort_result(control,cursor)
                    raise FixtureLimit("The submission changed too much fixture data. Limit changes to the records required by the challenge.")
                rows.append(row)
            state[table]=sorted(rows,key=repr)
    return state


def probe(connection, sql, job):
    try:
        rows = execute(connection,[sql],job)
        return {"results":rows,"error":None,"sqlstate":None}
    except pymysql.MySQLError as exc:
        job.check()
        if exc.args and exc.args[0] in INFRASTRUCTURE_ERRORS:
            raise EngineError("database_unavailable","The grading database connection was interrupted. Please retry.",503) from exc
        # PyMySQL exceptions expose errno/message but discard the SQLSTATE.
        # Read diagnostics on this same restricted connection before another
        # statement replaces the failing call's diagnostic information.
        with connection.cursor() as diagnostic:
            # RESIGNAL can retain the original condition before the final one.
            diagnostic.execute("GET DIAGNOSTICS @querylab_condition_count = NUMBER")
            diagnostic.execute("GET DIAGNOSTICS CONDITION @querylab_condition_count @querylab_error_state = RETURNED_SQLSTATE")
            diagnostic.execute("SELECT @querylab_error_state")
            sqlstate = diagnostic.fetchone()[0]
        return {"results":[],"error":list(exc.args[:2]),"sqlstate":sqlstate}


def equal_probe(actual, expected):
    if actual["error"] != expected["error"] or actual.get("sqlstate") != expected.get("sqlstate"):
        return False
    a, e = actual["results"], expected["results"]
    return len(a)==len(e) and all(same_result(x,y) and not x["truncated"] for x,y in zip(a,e))


def inventory_behavior(result, state):
    """Compare business identities, without requiring an incidental insert order.

    Auto-increment gaps survive rollback. Transfer request keys identify those
    records; linked movement IDs have no business meaning or inbound references.
    Keep the IDs of existing unlinked ledger records so unrelated edits still fail.
    """
    transfer_keys = {row[0]:row[1] for row in state["transfers"]}
    normalized = dict(state)
    normalized["transfers"] = sorted((tuple(row[1:]) for row in state["transfers"]),key=repr)
    movements = []
    for row in state["stock_movements"]:
        identifier = row[0] if row[5] is None and row[6] is None else None
        transfer = transfer_keys.get(row[5],row[5])
        movements.append((identifier,*row[1:5],transfer,row[6]))
    normalized["stock_movements"] = sorted(movements,key=repr)
    results = []
    for item in result["results"]:
        rows = [list(row) for row in item["rows"]]
        if "transfer_id" in item["columns"]:
            index = item["columns"].index("transfer_id")
            for row in rows:
                row[index] = transfer_keys.get(row[index],row[index])
        results.append({**item,"rows":rows})
    return {**result,"results":results}, normalized


def same_behavior(actual_result, expected_result, actual, expected, challenge):
    actual_state, expected_state = snapshot(actual), snapshot(expected)
    if challenge["id"] in {"BI-P01","BI-P02"}:
        actual_result, actual_state = inventory_behavior(actual_result,actual_state)
        expected_result, expected_state = inventory_behavior(expected_result,expected_state)
    return equal_probe(actual_result,expected_result) and actual_state==expected_state


def routine_signature(workspace, challenge):
    with connect() as control, control.cursor() as cursor:
        name = challenge.get("routine_name") or ("loyalty_tier" if challenge["type"]=="function" else "issue_refund")
        cursor.execute("SELECT ROUTINE_TYPE,SECURITY_TYPE,DTD_IDENTIFIER FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA=%s AND ROUTINE_NAME=%s",(workspace.schema,name))
        routine = cursor.fetchone()
        cursor.execute("SELECT PARAMETER_MODE,PARAMETER_NAME,DTD_IDENTIFIER FROM information_schema.PARAMETERS WHERE SPECIFIC_SCHEMA=%s AND SPECIFIC_NAME=%s ORDER BY ORDINAL_POSITION",(workspace.schema,name))
        parameters = cursor.fetchall()
        return routine,parameters


def json_tree(value):
    if isinstance(value,dict): return {k:json_tree(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)): return [json_tree(v) for v in value]
    return json_value(value)


def grade(challenge, statements, job):
    checks=[]
    for variant in (0,1,2):
        job.check()
        actual = provision(challenge["dataset"],variant,challenge["type"])
        expected = None
        connection = None
        try:
            if challenge["type"]=="query":
                reference = control_results(actual,challenge["solution"])
                connection = learner_connection(actual,job)
                rows = execute(connection,statements,job)
                ok = len(rows)==1 and not rows[0]["truncated"] and same_result(rows[0],reference)
                checks.append(dict(name="Practice fixture" if variant==0 else f"Unseen fixture {variant}",passed=ok,
                    message="Columns, ordered rows and values match." if ok else (challenge.get("query_feedback") or "Check aggregation, identities, date boundaries and the required column and row order.")))
            else:
                expected = provision(challenge["dataset"],variant,challenge["type"])
                connection = learner_connection(actual,job)
                execute(connection,statements,job)
                # Define the authored reference with its own equally restricted
                # connection. Even a submitted SECURITY INVOKER routine is never
                # called with root/control credentials.
                reference_connection = connect(user=expected.user,password=expected.password,database=expected.schema,streaming=True)
                try:
                    execute(reference_connection,[challenge["solution"]],job)
                    if routine_signature(actual,challenge) != routine_signature(expected,challenge):
                        checks.append(dict(name="Routine contract",passed=False,message="Check the routine name, parameter names/types/order, return type and SQL SECURITY INVOKER."))
                        return dict(passed=False,checks=checks)
                    if challenge["id"]=="OS-F01":
                        calls = [(f"SELECT loyalty_tier({value}) AS loyalty_tier",label) for value,label in [
                            ("NULL","Unknown input"),("0","Zero spending"),("499.99","Below silver"),("500","Silver boundary"),
                            ("500.01","Above silver"),("1999.99","Below gold"),("2000","Gold boundary"),("4999.99","Below platinum"),
                            ("5000","Platinum boundary"),("99999999.99","High spending"),("-0.01","Negative input")]]
                    elif challenge["id"]=="OS-P01":
                        calls=refund_probes(variant)
                    elif challenge["id"]=="OS-F02":
                        calls=online_expansion.routine_probes(challenge["id"],variant)
                    elif challenge["id"]=="BI-F01":
                        calls=inventory_expansion.routine_probes(challenge["id"],variant)
                    else:
                        calls=inventory_procedures.routine_probes(challenge["id"],variant)
                    if not calls:
                        raise RuntimeError("A routine requires an authored grading specification.")
                    for sql,label in calls:
                        job.check()
                        # Swap the kill target to the connection currently doing
                        # work. It is always a restricted execution account.
                        with job.connection_lock: job.connection_id=reference_connection.thread_id()
                        expected_result=probe(reference_connection,sql,job)
                        with job.connection_lock: job.connection_id=connection.thread_id()
                        actual_result=probe(connection,sql,job)
                        ok=same_behavior(actual_result,expected_result,actual,expected,challenge)
                        checks.append(dict(name=label+("" if variant==0 else f" · unseen {variant}"),passed=ok,
                            message="Behavior and business data match the contract." if ok else "Check return columns/values, exact error messages, retry behavior and unchanged data on failure."))
                    if challenge["id"]=="OS-P01":
                        # An unexpected insert failure must propagate and roll
                        # back. Injected only by control plane, never by learner.
                        for workspace in (actual,expected):
                            with connect(database=workspace.schema) as admin, admin.cursor() as cursor:
                                cursor.execute("CREATE TRIGGER fail_refund BEFORE INSERT ON refunds FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INJECTED_FAILURE'")
                        shift=variant*100
                        sql=f"CALL issue_refund('injected',{2+shift},{2+shift},1,'2026-06-30')"
                        with job.connection_lock: job.connection_id=reference_connection.thread_id()
                        e=probe(reference_connection,sql,job)
                        with job.connection_lock: job.connection_id=connection.thread_id()
                        a=probe(connection,sql,job)
                        ok=equal_probe(a,e) and snapshot(actual)==snapshot(expected)
                        checks.append(dict(name="Unexpected database failure",passed=ok,message="Failure propagates without partial changes." if ok else "Rollback and rethrow unexpected database errors; do not return success."))
                    elif challenge["type"]=="procedure":
                        for failure in inventory_procedures.rollback_probes(challenge["id"],variant):
                            for workspace in (actual,expected):
                                with connect(database=workspace.schema) as admin, admin.cursor() as cursor:
                                    for setup_sql in failure["setup_sql"]:
                                        cursor.execute(setup_sql)
                            with job.connection_lock: job.connection_id=reference_connection.thread_id()
                            e=probe(reference_connection,failure["sql"],job)
                            with job.connection_lock: job.connection_id=connection.thread_id()
                            a=probe(connection,failure["sql"],job)
                            ok=same_behavior(a,e,actual,expected,challenge)
                            checks.append(dict(name=failure["label"]+("" if variant==0 else f" · unseen {variant}"),passed=ok,
                                message="Failure propagates without partial changes." if ok else "Rollback all stock, ledger and operation changes, then propagate the database error."))
                finally:
                    reference_connection.close()
        except FixtureLimit as exc:
            checks.append(dict(name="Fixture integrity",passed=False,message=str(exc)))
            return dict(passed=False,checks=checks)
        except pymysql.MySQLError as exc:
            job.check()
            if exc.args and exc.args[0] in INFRASTRUCTURE_ERRORS:
                raise EngineError("database_unavailable","The grading database connection was interrupted. Please retry.",503) from exc
            # Database errors can include values (for example invalid JSON or
            # geometry text). Do not expose hidden fixture values in feedback.
            checks.append(dict(name="Executable SQL",passed=False,message=safe_sql_error(exc,actual) if variant==0 else "The submission could not execute against an independent fixture. Check the published schema and edge cases."))
        finally:
            close_learner(connection,job)
            destroy(actual)
            if expected: destroy(expected)
    return dict(passed=bool(checks) and all(c["passed"] for c in checks),checks=checks)


def refund_probes(variant):
    shift=variant*100
    def call(key,item,payment,amount,at="'2026-06-30 12:00:00'"):
        return f"CALL issue_refund({key},{item+shift},{payment+shift},{amount},{at})"
    return [
        (call("'partial'",1,1,25),"Partial refund"),
        (call("'partial'",1,1,25),"Exact request replay"),
        (call("'second'",1,1,10),"Second request"),
        (call("'partial'",1,1,25),"Replay preserves original balance"),
        (call("'partial'",1,1,26),"Conflicting request"),
        (call("'too-much'",1,1,9999),"Item budget exceeded"),
        (call("'exact'",3,3,500),"Exact remaining item budget"),
        (call("'empty'",3,3,1),"Exhausted item budget"),
        (call("'payment-limit'",1,20,201),"Payment budget independently enforced"),
        (call("'wrong-order'",1,2,1),"Wrong-order payment"),
        (call("'cancelled-order'",6,6,1),"Cancelled order"),
        (call("'failed-payment'",1,21,1),"Failed payment"),
        (call("'early-time'",2,2,1,"'2026-01-01'"),"Refund before capture"),
        (call("'unknown'",9999,1,1),"Missing item"),
        (call("'unknown-payment'",1,9999,1),"Missing payment"),
        (call("'zero'",1,1,0),"Zero amount"),
        (call("'negative'",1,1,-1),"Negative amount"),
        (call("'   '",1,1,1),"Blank request key"),
        (call("NULL",1,1,1),"NULL request key"),
        (f"CALL issue_refund('null-item',NULL,{1+shift},1,'2026-06-30')","NULL item identifier"),
        (f"CALL issue_refund('null-payment',{1+shift},NULL,1,'2026-06-30')","NULL payment identifier"),
        (f"CALL issue_refund('null-amount',{1+shift},{1+shift},NULL,'2026-06-30')","NULL amount"),
        (call("'null-time'",1,1,1,"NULL"),"NULL timestamp"),
    ]


def safe_sql_error(exc, workspace=None):
    if exc.args and exc.args[0] in {1045,2002,2003,2006,2013}:
        return "The database connection is unavailable. Try again shortly."
    message = str(exc.args[1] if len(exc.args)>1 else "SQL could not execute.")[:500]
    if workspace:
        message=message.replace(workspace.schema,"workspace").replace(workspace.user,"learner")
    return message


class Engine:
    def __init__(self):
        self.sessions={}
        self.jobs={}
        self.lock=threading.RLock()
        self.pool=ThreadPoolExecutor(max_workers=4,thread_name_prefix="querylab")
        self.stopped=threading.Event()
        self.initialization_lock=threading.Lock()
        self.initialized=False
        self.cleanup_started=False
        self.database_status={"connected":False,"message":"Waiting for MySQL."}

    def startup(self):
        workspace_namespace()
        try:
            self.check_database()
        except EngineError:
            if os.getenv("QUERYLAB_HELPER_MODE", "false").lower() != "true":
                raise
        if not self.cleanup_started:
            self.cleanup_started=True
            threading.Thread(target=self.sweep,daemon=True,name="querylab-cleanup").start()

    def check_database(self):
        # The lock also serializes first successful initialization after an
        # unavailable database. Later checks must never erase live workspaces.
        with self.initialization_lock:
            try:
                with connect() as control, control.cursor() as cursor:
                    version=validate_server(cursor)
                    if not self.initialized:
                        cursor.execute("SHOW DATABASES")
                        schemas=[r[0] for r in cursor.fetchall() if owned_identifier(r[0])]
                        cursor.execute("SELECT User,Host FROM mysql.user")
                        users=[r for r in cursor.fetchall() if owned_identifier(r[0],user=True) and r[1]=="%"]
                        for schema in schemas: cursor.execute(f"DROP DATABASE `{schema}`")
                        for user,host in users: cursor.execute("DROP USER IF EXISTS %s@%s",(user,host))
                        self.initialized=True
                self.database_status={"connected":True,"version":version}
            except EngineError as exc:
                self.database_status={"connected":False,"message":exc.message}
                raise
            except (pymysql.MySQLError, OSError, ValueError, OverflowError) as exc:
                self.database_status={"connected":False,"message":"Cannot connect to MySQL. Check the local helper's MYSQL_HOST, MYSQL_PORT, credentials and permissions, and ensure MySQL is running."}
                raise EngineError("database_unavailable",self.database_status["message"],503) from exc
        return self.database_status.copy()

    def shutdown(self):
        self.stopped.set()
        for job in list(self.jobs.values()):
            if job.status in {"queued","running"}: job.stop()
        self.pool.shutdown(wait=True,cancel_futures=True)
        for session in list(self.sessions.values()):
            for workspace in session.workspaces.values(): destroy(workspace)

    def sweep(self):
        while not self.stopped.wait(20):
            self.reap_once()

    def reap_once(self,now=None):
        now=time.time() if now is None else now
        expired=[]
        with self.lock:
            for token,session in list(self.sessions.items()):
                if session.expires<now and not session.busy:
                    expired.extend(session.workspaces.values())
                    del self.sessions[token]
            for id,job in list(self.jobs.items()):
                if job.owner not in self.sessions and job.status not in {"queued","running"}:
                    del self.jobs[id]
        for workspace in expired:destroy(workspace)

    def session(self,token=None,create=False):
        with self.lock:
            session=self.sessions.get(token)
            if session and (session.expires>time.time() or session.busy):
                session.expires=time.time()+TTL
                return session,False
            if not create:
                raise EngineError("session_expired","Your practice session expired. Start a new session; browser drafts are preserved.",401)
            active=sum(s.expires>time.time() or s.busy for s in self.sessions.values())
            if active>=MAX_SESSIONS:
                raise EngineError("capacity_reached",f"All {MAX_SESSIONS} practice places are in use. Try again shortly.",429)
            session=Session(secrets.token_urlsafe(32),time.time()+TTL)
            self.sessions[session.token]=session
            return session,True

    def workspace(self,session,dataset):
        if dataset not in session.workspaces:
            session.workspaces[dataset]=provision(dataset)
        return session.workspaces[dataset]

    def queue(self,session,challenge,sql,mode):
        if not challenge["ready"]:
            raise EngineError("challenge_not_ready","This challenge is still being authored. Choose an available challenge.",422)
        try: statements=validate_script(sql,grading_type=challenge["type"] if mode=="submit" else None)
        except SQLPolicyError as exc: raise EngineError("sql_policy",str(exc),422) from exc
        with self.lock:
            if session.busy: raise EngineError("workspace_busy","Finish or cancel the active operation before starting another.",409)
            session.busy=True
            job=Job(uuid.uuid4().hex,session.token,challenge["id"],mode)
            self.jobs[job.id]=job
            # Keep memory bounded even for a long-lived visitor.
            old=[j for j in self.jobs.values() if j.owner==session.token and j.status not in {"running","queued"}]
            for past in sorted(old,key=lambda j:j.created)[:-24]: self.jobs.pop(past.id,None)
            self.pool.submit(self.work,session,job,challenge,statements)
            return dict(job_id=job.id,status="queued")

    def work(self,session,job,challenge,statements):
        started=time.monotonic()
        timer=threading.Timer(TIMEOUT,lambda:job.stop(timeout=True))
        connection=None
        workspace=None
        try:
            job.check()
            job.status="running"
            timer.start()
            if job.mode=="submit":
                grading=grade(challenge,statements,job)
                result=dict(mode="submit",result_sets=[],grading=grading)
            else:
                workspace=self.workspace(session,challenge["dataset"])
                connection=learner_connection(workspace,job)
                rows=execute(connection,statements,job)
                result=dict(mode="run",result_sets=rows)
            job.check()
            result["elapsed_ms"]=round((time.monotonic()-started)*1000)
            job.result=json_tree(result)
            job.status="completed"
        except EngineError as exc:
            job.error=dict(code=exc.code,message=exc.message)
            job.status="cancelled" if exc.code=="cancelled" else "failed"
        except pymysql.MySQLError as exc:
            job.status="cancelled" if job.cancelled.is_set() and not job.timed_out else "failed"
            unavailable=bool(exc.args and exc.args[0] in INFRASTRUCTURE_ERRORS)
            job.error=dict(code="execution_timeout" if job.timed_out else ("cancelled" if job.cancelled.is_set() else ("database_unavailable" if unavailable else "sql_error")),
                           message=f"Execution exceeded {TIMEOUT} seconds and was stopped." if job.timed_out else ("Execution was cancelled." if job.cancelled.is_set() else safe_sql_error(exc,workspace)))
        except Exception:
            log.exception("Job failed",extra={"job_id":job.id})
            job.error=dict(code="internal_error",message="The SQL workspace could not complete this operation. Please try again.")
            job.status="failed"
        finally:
            timer.cancel()
            close_learner(connection,job)
            with self.lock: session.busy=False
            log.info("job_finished job_id=%s mode=%s status=%s elapsed_ms=%d",job.id,job.mode,job.status,round((time.monotonic()-started)*1000))

    def own_job(self,session,id):
        job=self.jobs.get(id)
        if not job or job.owner!=session.token: raise EngineError("job_not_found","Job not found.",404)
        return job

    def schema(self,session,dataset):
        with self.lock:
            if session.busy: raise EngineError("workspace_busy","Wait for the active SQL operation before inspecting tables.",409)
            session.busy=True
        try:
            workspace=self.workspace(session,dataset)
            tables=[]
            relationships=[]
            with connect(database=workspace.schema) as control, control.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                names=[r[0] for r in cursor.fetchall()]
                for table in names:
                    cursor.execute(f"SHOW COLUMNS FROM `{table}`")
                    columns=[dict(name=r[0],type=r[1],nullable=r[2]=="YES",key=r[3]) for r in cursor.fetchall()]
                    cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                    tables.append(dict(name=table,columns=columns,row_count=cursor.fetchone()[0]))
                cursor.execute("SELECT TABLE_NAME,COLUMN_NAME,REFERENCED_TABLE_NAME,REFERENCED_COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE WHERE TABLE_SCHEMA=%s AND REFERENCED_TABLE_NAME IS NOT NULL",(workspace.schema,))
                relationships=[dict(from_table=r[0],from_column=r[1],to_table=r[2],to_column=r[3]) for r in cursor.fetchall()]
            return dict(dataset=dataset,tables=tables,relationships=relationships)
        finally:
            with self.lock: session.busy=False

    def sample(self,session,dataset,table):
        allowed={t["name"] for t in self.schema(session,dataset)["tables"]}
        if table not in allowed: raise EngineError("table_not_found","Choose a table from this dataset.",404)
        with self.lock:
            if session.busy: raise EngineError("workspace_busy","Wait for the active operation.",409)
            session.busy=True
        try:
            result=control_results(session.workspaces[dataset],f"SELECT * FROM `{table}` LIMIT 11")
            result["truncated"]=len(result["rows"])>10
            result["rows"]=result["rows"][:10]
            return json_tree(result)
        finally:
            with self.lock:session.busy=False

    def reset(self,session,dataset):
        with self.lock:
            if session.busy:raise EngineError("workspace_busy","Finish or cancel the active operation before resetting.",409)
            session.busy=True
        try:
            replacement=provision(dataset)
            old=session.workspaces.get(dataset)
            session.workspaces[dataset]=replacement
            if old:destroy(old)
        finally:
            with self.lock:session.busy=False


engine=Engine()


def expires_at(session):
    return datetime.fromtimestamp(session.expires,timezone.utc).isoformat()
