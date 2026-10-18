from contextlib import asynccontextmanager
import logging
import os
from urllib.parse import urlparse

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field
import pymysql

from .content.challenges import CHALLENGES, BY_ID, public
from .content.datasets import DATASETS
from .engine import engine, EngineError, TTL, connect, expires_at
from . import helper

logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(name)s %(message)s")
COOKIE="querylab_session"
COOKIE_SECURE=os.getenv("QUERYLAB_COOKIE_SECURE","false").lower()=="true"


@asynccontextmanager
async def lifespan(app):
    helper.validate_configuration()
    engine.startup()
    yield
    engine.shutdown()


app=FastAPI(title="QueryLab",version="0.1.0",lifespan=lifespan,docs_url=None,redoc_url=None)


@app.exception_handler(EngineError)
async def handle_engine_error(request,exc):
    return JSONResponse(status_code=exc.status,content={"error":{"code":exc.code,"message":exc.message}})


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request,exc):
    message="Provide the pairing code shown by your local helper." if request.url.path=="/api/helper/pair" else "Provide a valid challenge_id and SQL script of at most 32 KB."
    return JSONResponse(status_code=422,content={"error":{"code":"invalid_request","message":message}})


@app.exception_handler(pymysql.MySQLError)
async def handle_database_error(request,exc):
    logging.getLogger("querylab").error("Database request failed path=%s errno=%s",request.url.path,exc.args[0] if exc.args else "unknown")
    return JSONResponse(status_code=503,content={"error":{"code":"database_unavailable","message":"The practice database is temporarily unavailable. Try again shortly."}})


@app.middleware("http")
async def request_policy(request:Request,call_next):
    if helper.enabled():
        response=await helper.request_policy(request,call_next,engine)
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["Cache-Control"]="no-store"
        response.headers["X-Frame-Options"]="DENY"
        return response
    if request.method in {"POST","PUT","PATCH","DELETE"}:
        origin=request.headers.get("origin")
        # SameSite cookie plus browser Origin checks. Explicit allowed origin is
        # needed only when reverse proxy host differs from the API host.
        configured=os.getenv("QUERYLAB_PUBLIC_ORIGIN","").rstrip("/")
        if origin:
            expected=configured or f"{request.url.scheme}://{request.headers.get('host','')}"
            if origin.rstrip("/")!=expected:
                return JSONResponse(status_code=403,content={"error":{"code":"origin_forbidden","message":"Use QueryLab from its own website."}})
        if request.headers.get("sec-fetch-site")=="cross-site":
            return JSONResponse(status_code=403,content={"error":{"code":"origin_forbidden","message":"Cross-site operations are not allowed."}})
    response=await call_next(request)
    token=request.cookies.get(COOKIE)
    if token in engine.sessions and response.status_code!=401:
        response.set_cookie(COOKIE,token,max_age=TTL,httponly=True,secure=COOKIE_SECURE,samesite="strict",path="/api")
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["Cache-Control"]="no-store"
    response.headers["X-Frame-Options"]="DENY"
    return response


class SQLRequest(BaseModel):
    challenge_id:str=Field(min_length=1,max_length=20)
    sql:str=Field(min_length=1,max_length=32000)


class ResetRequest(BaseModel):
    challenge_id:str=Field(min_length=1,max_length=20)


def get_challenge(id):
    if id not in BY_ID:raise EngineError("challenge_not_found","Challenge not found.",404)
    return BY_ID[id]


def session_for(request):
    if helper.enabled():return helper.bearer_session(request,engine)
    return engine.session(request.cookies.get(COOKIE))[0]


class PairRequest(BaseModel):
    pairing_code:str=Field(min_length=1,max_length=256)


@app.get("/",response_class=HTMLResponse,include_in_schema=False)
def helper_home():
    if not helper.enabled():raise EngineError("helper_disabled","Local helper mode is not enabled.",404)
    return HTMLResponse("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QueryLab local helper</title>
<style>body{margin:0;background:#111719;color:#edf4f2;font:16px/1.65 system-ui,sans-serif}main{max-width:36rem;margin:12vh auto;padding:2rem}h1{line-height:1.2;font-size:2rem}a{color:#8ae6bd}a:focus-visible{outline:2px solid #8ae6bd;outline-offset:4px}p{color:#bac8c4}strong{color:#edf4f2}</style>
</head><body><main><h1>Your QueryLab helper is running.</h1>
<p>This is the local connection service. Open the QueryLab website to practise SQL.</p>
<p>Return to the QueryLab website. You can usually keep its prefilled <strong>Helper URL</strong> unchanged.</p>
<h2>Find your pairing code</h2>
<p>Open <strong>Start-QueryLab-Helper.cmd</strong> in your extracted Windows helper folder. In the setup window, choose <strong>Start helper</strong>, wait for MySQL to be ready, then choose <strong>Copy pairing code</strong>.</p>
<p>Paste the code into the website's <strong>Pairing code</strong> field and choose <strong>Pair helper</strong>. Reopening the launcher lets you retrieve it again.</p>
<details><summary>Using the command-line setup instead?</summary>
<p>On Windows, open PowerShell in the QueryLab folder you used to start this helper. Run:</p>
<pre><code>.\\scripts\\show-helper-code.ps1</code></pre>
<p>PowerShell prints <strong>Pairing code for your local helper</strong> followed by your private code. Copy the code into the website's <strong>Pairing code</strong> field, then choose <strong>Pair helper</strong>.</p>
</details>
<p>The helper generates this code during setup. It is separate from your MySQL password. The website does not display your code.</p>
<p><a href="/api/helper/status">View helper and MySQL status</a></p>
<p>Your database credentials stay on your computer.</p>
</main></body></html>""")


@app.get("/api/helper/status")
def helper_status():
    if not helper.enabled():raise EngineError("helper_disabled","Local helper mode is not enabled.",404)
    try:engine.check_database()
    except EngineError:pass
    return {"mode":"helper","version":"0.2.0","protocol_version":1,"requires_pairing":True,"database":engine.database_status.copy()}


@app.post("/api/helper/pair")
def pair_helper(body:PairRequest,request:Request):
    if not helper.enabled():raise EngineError("helper_disabled","Local helper mode is not enabled.",404)
    session=helper.pair(request,body.pairing_code,engine)
    return {"token":session.token,"expires_at":expires_at(session),"ttl_seconds":TTL}


@app.get("/api/datasets/{dataset}/setup.sql")
def dataset_setup(dataset:str):
    from .export import export_dataset
    try:sql=export_dataset(dataset)
    except ValueError:raise EngineError("dataset_not_found","Choose a valid dataset.",404)
    return Response(content=sql,media_type="application/sql",headers={"Content-Disposition":f'attachment; filename="querylab-{dataset}-v1.sql"'})


def dataset_for(challenge_id=None,dataset=None):
    if challenge_id:return get_challenge(challenge_id)["dataset"]
    if dataset not in DATASETS:raise EngineError("dataset_not_found","Choose a valid challenge or dataset.",404)
    return dataset


@app.get("/api/health")
def health():
    with connect() as database,database.cursor() as cursor:cursor.execute("SELECT 1")
    return {"status":"ok","database":"mysql","version":"0.1.0"}


@app.get("/api/challenges")
def challenges():return {"challenges":[public(c) for c in CHALLENGES]}


@app.get("/api/challenges/{id}/solution")
def solution(id:str):
    challenge=get_challenge(id)
    if not challenge["ready"]:raise EngineError("challenge_not_ready","An explained solution is still being authored.",422)
    return {"sql":challenge["solution"],"explanation":challenge["explanation"]}


@app.get("/api/challenges/{id}")
def detail(id:str):return public(get_challenge(id))


@app.post("/api/session")
def create_session(request:Request,response:Response):
    if helper.enabled():
        session=session_for(request)
        return {"expires_at":expires_at(session),"created":False,"ttl_seconds":TTL}
    session,created=engine.session(request.cookies.get(COOKIE),create=True)
    response.set_cookie(COOKIE,session.token,max_age=TTL,httponly=True,secure=COOKIE_SECURE,samesite="strict",path="/api")
    return {"expires_at":expires_at(session),"created":created,"ttl_seconds":TTL}


@app.post("/api/run",status_code=202)
def run(body:SQLRequest,request:Request):
    return engine.queue(session_for(request),get_challenge(body.challenge_id),body.sql,"run")


@app.post("/api/submit",status_code=202)
def submit(body:SQLRequest,request:Request):
    return engine.queue(session_for(request),get_challenge(body.challenge_id),body.sql,"submit")


@app.get("/api/jobs/{id}")
def job(id:str,request:Request):return engine.own_job(session_for(request),id).view()


@app.post("/api/jobs/{id}/cancel")
def cancel(id:str,request:Request):
    job=engine.own_job(session_for(request),id)
    if job.status in {"queued","running"}:job.stop()
    return job.view()


@app.post("/api/reset")
def reset(body:ResetRequest,request:Request):
    session=session_for(request)
    engine.reset(session,get_challenge(body.challenge_id)["dataset"])
    return {"message":"Practice data and routines were reset. Your editor draft is preserved.","expires_at":expires_at(session)}


@app.get("/api/schema")
def schema(request:Request,challenge_id:str|None=None,dataset:str|None=None):
    return engine.schema(session_for(request),dataset_for(challenge_id,dataset))


@app.get("/api/schema/sample")
def sample(request:Request,table:str,challenge_id:str|None=None,dataset:str|None=None):
    return engine.sample(session_for(request),dataset_for(challenge_id,dataset),table)
