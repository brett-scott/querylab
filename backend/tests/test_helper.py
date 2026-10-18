"""Transport/security contracts independent of a running MySQL server."""
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
import pymysql
import pytest

from app import helper, main
from app import engine as engine_module
from app.engine import Engine, EngineError, Job, Workspace, destroy, owned_identifier, validate_server


ORIGIN="http://localhost:8081"
PAIRING_CODE="unit-test-only-pairing-secret-123456789"


@pytest.fixture
def local_helper(monkeypatch):
    monkeypatch.setenv("QUERYLAB_HELPER_MODE","true")
    monkeypatch.setenv("QUERYLAB_PAIRING_TOKEN",PAIRING_CODE)
    monkeypatch.setenv("QUERYLAB_HELPER_ALLOWED_ORIGINS",ORIGIN+",https://querylab.example")
    monkeypatch.setenv("QUERYLAB_WORKSPACE_NAMESPACE","aabbccddeeff")
    current=Engine()
    current.initialized=True
    current.database_status={"connected":True,"version":"8.4.9"}
    monkeypatch.setattr(current,"check_database",lambda:current.database_status)
    monkeypatch.setattr(main,"engine",current)
    monkeypatch.setattr(helper,"pairing_limiter",helper.PairingLimiter())
    client=TestClient(main.app,base_url="http://127.0.0.1:8765")
    yield client,current
    client.close()
    current.shutdown()


def paired(client):
    response=client.post("/api/helper/pair",json={"pairing_code":PAIRING_CODE},headers={"Origin":ORIGIN})
    assert response.status_code==200,response.text
    assert "set-cookie" not in response.headers
    return {"Authorization":"Bearer "+response.json()["token"],"Origin":ORIGIN}


def test_public_status_contains_only_protocol_and_safe_readiness(local_helper):
    client,_=local_helper
    response=client.get("/api/helper/status",headers={"Origin":ORIGIN})
    assert response.status_code==200
    assert response.json()=={"mode":"helper","version":"0.2.0","protocol_version":1,"requires_pairing":True,"database":{"connected":True,"version":"8.4.9"}}
    assert response.headers["access-control-allow-origin"]==ORIGIN
    assert "access-control-allow-credentials" not in response.headers


def test_helper_base_url_explains_how_to_connect_without_exposing_secrets(local_helper,monkeypatch):
    client,_=local_helper
    monkeypatch.setenv("MYSQL_ROOT_PASSWORD","private-database-password-for-test")
    response=client.get("/")
    assert response.status_code==200
    assert response.headers["content-type"].startswith("text/html")
    assert "Your QueryLab helper is running." in response.text
    assert "Helper URL" in response.text and "Pair helper" in response.text
    assert "prefilled" in response.text
    assert "Start-QueryLab-Helper.cmd" in response.text
    assert "Copy pairing code" in response.text
    assert ".\\scripts\\show-helper-code.ps1" in response.text
    assert "open PowerShell in the QueryLab folder" in response.text
    assert 'href="/api/helper/status"' in response.text
    assert PAIRING_CODE not in response.text
    assert "private-database-password-for-test" not in response.text
    assert "set-cookie" not in response.headers
    assert client.get("/api/challenges").status_code==401


def test_helper_base_page_is_not_exposed_in_legacy_mode(local_helper,monkeypatch):
    client,_=local_helper
    monkeypatch.setenv("QUERYLAB_HELPER_MODE","false")
    assert client.get("/").status_code==404


@pytest.mark.parametrize("path",["/api/challenges","/api/challenges/OS-Q01","/api/challenges/OS-Q01/solution","/api/schema?dataset=online-store","/api/jobs/unknown","/api/health","/api/datasets/online-store/setup.sql"])
def test_all_api_reads_require_pairing(local_helper,path):
    client,current=local_helper
    assert client.get(path).status_code==401
    session,_=current.session(create=True)
    client.cookies.set(main.COOKIE,session.token)
    assert client.get(path).status_code==401 # cookies never authorize helper operations


@pytest.mark.parametrize("body",[{}, {"pairing_code":"wrong"}, {"pairing_code":""}])
def test_missing_bad_or_empty_pairing_code_rejected(local_helper,body):
    client,_=local_helper
    assert client.post("/api/helper/pair",json=body).status_code in {401,422}


def test_pairing_rate_limit(local_helper):
    client,_=local_helper
    for _ in range(8):
        assert client.post("/api/helper/pair",json={"pairing_code":"wrong"}).status_code==401
    assert client.post("/api/helper/pair",json={"pairing_code":PAIRING_CODE}).status_code==429


def test_bearer_session_does_not_create_extra_sessions_or_cookies(local_helper):
    client,current=local_helper
    headers=paired(client)
    assert client.get("/api/challenges",headers=headers).status_code==200
    response=client.post("/api/session",headers=headers,json={})
    assert response.status_code==200 and not response.json()["created"]
    assert len(current.sessions)==1
    assert "set-cookie" not in response.headers
    assert client.get("/api/challenges",headers={"Authorization":"Bearer invalid"}).status_code==401


def test_expired_and_other_sessions_cannot_access_jobs(local_helper):
    client,current=local_helper
    first=paired(client)
    first_token=first["Authorization"].split()[1]
    second=paired(client)
    current.jobs["owned-job"]=Job("owned-job",first_token,"OS-Q01","run",status="completed")
    assert client.get("/api/jobs/owned-job",headers=first).status_code==200
    assert client.get("/api/jobs/owned-job",headers=second).status_code==404
    assert client.post("/api/jobs/owned-job/cancel",headers=second).status_code==404
    current.sessions[first_token].expires=0
    assert client.get("/api/challenges",headers=first).status_code==401


@pytest.mark.parametrize("origin",["null","https://evil.example",ORIGIN+".evil.example","http://localhost:8082",ORIGIN+"/"])
@pytest.mark.parametrize("method,path",[("GET","/"),("GET","/api/helper/status"),("GET","/api/challenges"),("POST","/api/helper/pair"),("OPTIONS","/api/helper/status")])
def test_exact_origin_policy_applies_to_all_methods(local_helper,origin,method,path):
    client,_=local_helper
    response=client.request(method,path,headers={"Origin":origin})
    assert response.status_code==403
    assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("host",["evil.example:8765","localhost.evil.example:8765","127.0.0.1.evil.example","attacker@127.0.0.1:8765"])
def test_dns_rebinding_host_rejected(local_helper,host):
    client,_=local_helper
    assert client.get("/api/helper/status",headers={"Host":host,"Origin":ORIGIN}).status_code==403
    assert client.get("/",headers={"Host":host}).status_code==403


def test_authorization_preflight_and_private_network_access(local_helper):
    client,_=local_helper
    response=client.options("/api/run",headers={"Origin":ORIGIN,"Access-Control-Request-Method":"POST","Access-Control-Request-Headers":"authorization,content-type","Access-Control-Request-Private-Network":"true"})
    assert response.status_code==204
    assert response.headers["access-control-allow-origin"]==ORIGIN
    assert response.headers["access-control-allow-private-network"]=="true"
    assert "access-control-allow-credentials" not in response.headers


def test_unavailable_database_does_not_prevent_pairing(local_helper,monkeypatch):
    client,current=local_helper
    current.initialized=False
    current.database_status={"connected":False,"message":"Start MySQL and retry."}
    def unavailable():raise EngineError("database_unavailable","Start MySQL and retry.",503)
    monkeypatch.setattr(current,"check_database",unavailable)
    assert client.get("/api/helper/status").json()["database"]["connected"] is False
    headers=paired(client)
    assert client.post("/api/session",headers=headers).status_code==200
    assert client.get("/api/schema?dataset=online-store",headers=headers).status_code==503


@pytest.mark.parametrize("version",["8.0.44","9.0.1","8.4.9-MariaDB","10.11.9-MariaDB"])
def test_unsupported_versions_never_reach_cleanup(monkeypatch,version):
    monkeypatch.setenv("QUERYLAB_WORKSPACE_NAMESPACE","aabbccddeeff")
    cursor=MagicMock()
    cursor.fetchone.return_value=(version,4194304,1,1)
    connection=MagicMock()
    connection.__enter__.return_value=connection
    connection.cursor.return_value.__enter__.return_value=cursor
    monkeypatch.setattr(engine_module,"connect",lambda **kwargs:connection)
    current=Engine()
    try:
        with pytest.raises(EngineError):current.check_database()
        assert len(cursor.execute.call_args_list)==1
        assert "VERSION()" in cursor.execute.call_args_list[0].args[0]
        assert not current.initialized
    finally:current.shutdown()


def test_failed_connection_status_does_not_leak_credentials(monkeypatch):
    def unavailable(**kwargs):raise pymysql.OperationalError(1045,"Access denied for secret-user secret-password")
    monkeypatch.setattr(engine_module,"connect",unavailable)
    current=Engine()
    try:
        with pytest.raises(EngineError):current.check_database()
        assert "secret" not in str(current.database_status)
    finally:current.shutdown()


def test_offline_startup_keeps_one_cleanup_thread_and_can_be_retried(monkeypatch):
    monkeypatch.setenv("QUERYLAB_HELPER_MODE","true")
    monkeypatch.setenv("QUERYLAB_WORKSPACE_NAMESPACE","aabbccddeeff")
    def unavailable(**kwargs):raise pymysql.OperationalError(2003,"private connection details")
    monkeypatch.setattr(engine_module,"connect",unavailable)
    thread=MagicMock()
    monkeypatch.setattr(engine_module.threading,"Thread",thread)
    current=Engine()
    try:
        current.startup()
        current.startup()
        assert not current.initialized
        assert current.database_status["connected"] is False
        assert "private" not in current.database_status["message"]
        thread.assert_called_once()
        thread.return_value.start.assert_called_once()
    finally:current.shutdown()


def test_oversized_packet_and_binary_log_require_actionable_configuration():
    cursor=MagicMock()
    cursor.fetchone.return_value=("8.4.9",64*1024*1024,1,1)
    with pytest.raises(EngineError,match="max_allowed_packet=4M"):validate_server(cursor)
    cursor.fetchone.return_value=("8.4.9",4194304,1,0)
    with pytest.raises(EngineError,match="log_bin_trust_function_creators"):validate_server(cursor)


def test_namespace_guards_never_delete_arbitrary_objects(local_helper,monkeypatch):
    client,_=local_helper
    connection=MagicMock()
    monkeypatch.setattr(engine_module,"connect",connection)
    for schema,user in [("important_production","root"),("ql_"+"f"*24,"qlu_"+"f"*24),("ql_112233445566_"+"f"*24,"qlu_112233445566_"+"f"*12)]:
        with pytest.raises(EngineError):destroy(Workspace(schema,user,"unused","online-store"))
    connection.assert_not_called()
    assert owned_identifier("ql_aabbccddeeff_"+"f"*24)
    assert owned_identifier("qlu_aabbccddeeff_"+"f"*12,user=True)


def test_helper_configuration_rejects_missing_namespace_and_wildcard(monkeypatch):
    monkeypatch.setenv("QUERYLAB_HELPER_MODE","true")
    monkeypatch.delenv("QUERYLAB_WORKSPACE_NAMESPACE",raising=False)
    with pytest.raises(RuntimeError):engine_module.workspace_namespace()
    monkeypatch.setenv("QUERYLAB_PAIRING_TOKEN",PAIRING_CODE)
    monkeypatch.setenv("QUERYLAB_HELPER_ALLOWED_ORIGINS","*")
    with pytest.raises(RuntimeError):helper.validate_configuration()


def test_legacy_cookie_mode_remains_available(monkeypatch):
    monkeypatch.setenv("QUERYLAB_HELPER_MODE","false")
    current=Engine()
    monkeypatch.setattr(main,"engine",current)
    client=TestClient(main.app,base_url="http://testserver")
    try:
        response=client.post("/api/session")
        assert response.status_code==200
        assert main.COOKIE in response.cookies
        assert client.get("/api/challenges").status_code==200
    finally:
        client.close()
        current.shutdown()
