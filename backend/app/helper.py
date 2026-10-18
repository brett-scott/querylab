"""Loopback helper transport. MySQL credentials never enter this API."""
from collections import defaultdict, deque
import os
import secrets
import threading
import time
from urllib.parse import urlsplit

from fastapi.responses import JSONResponse, Response

from .engine import EngineError


def enabled():
    return os.getenv("QUERYLAB_HELPER_MODE", "false").lower() == "true"


def allowed_origins():
    origins=set(filter(None,(value.strip() for value in os.getenv("QUERYLAB_HELPER_ALLOWED_ORIGINS", "").split(","))))
    for origin in origins:
        parsed=urlsplit(origin)
        if parsed.scheme not in {"http","https"} or not parsed.hostname or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise RuntimeError("QUERYLAB_HELPER_ALLOWED_ORIGINS must contain exact HTTP(S) origins without paths or wildcards.")
    return origins


def validate_configuration():
    if enabled():
        if len(os.getenv("QUERYLAB_PAIRING_TOKEN", "")) < 24:
            raise RuntimeError("Set QUERYLAB_PAIRING_TOKEN to a random secret of at least 24 characters.")
        if not allowed_origins():
            raise RuntimeError("Set QUERYLAB_HELPER_ALLOWED_ORIGINS to the exact frontend origin(s).")


def error(code, message, status):
    return JSONResponse(status_code=status,content={"error":{"code":code,"message":message}})


def host_allowed(request):
    # Loopback names only, including container-local health checks. A public
    # hostname resolving to loopback must never bypass this DNS-rebinding gate.
    try:
        parsed=urlsplit("http://"+request.headers.get("host", ""))
        return parsed.hostname in {"localhost","127.0.0.1","::1"} and not parsed.username and not parsed.password and not parsed.path and not parsed.query and not parsed.fragment
    except ValueError:
        return False


def cors_headers(origin):
    return {"Access-Control-Allow-Origin":origin,"Vary":"Origin"}


async def request_policy(request, call_next, engine):
    if not host_allowed(request):
        return error("host_forbidden","Connect to the helper using localhost or 127.0.0.1.",403)
    origin=request.headers.get("origin")
    if origin is not None and origin not in allowed_origins():
        return error("origin_forbidden","This website is not allowed by the local helper configuration.",403)
    if request.method == "OPTIONS":
        requested={header.strip().lower() for header in request.headers.get("access-control-request-headers", "").split(",") if header.strip()}
        if not origin or request.headers.get("access-control-request-method") not in {"GET","POST"} or not requested <= {"authorization","content-type"}:
            return error("preflight_forbidden","Unsupported helper request.",403)
        headers=cors_headers(origin)
        headers.update({"Access-Control-Allow-Methods":"GET, POST, OPTIONS","Access-Control-Allow-Headers":"Authorization, Content-Type","Access-Control-Max-Age":"600"})
        if request.headers.get("access-control-request-private-network") == "true":
            headers["Access-Control-Allow-Private-Network"]="true"
        return Response(status_code=204,headers=headers)
    try:
        if request.url.path.startswith("/api/") and request.url.path not in {"/api/helper/status","/api/helper/pair"}:
            bearer_session(request,engine)
            if not engine.initialized and request.url.path in {"/api/run","/api/submit","/api/reset","/api/schema","/api/schema/sample"}:
                # Startup may have happened before the learner started MySQL.
                # Initialize before creating any live learner workspaces.
                engine.check_database()
        response=await call_next(request)
    except EngineError as exc:
        response=error(exc.code,exc.message,exc.status)
    if origin:
        response.headers.update(cors_headers(origin))
    return response


def bearer_session(request,engine):
    authorization=request.headers.get("authorization", "")
    scheme, _, token=authorization.partition(" ")
    if scheme.lower() != "bearer" or not token or " " in token:
        raise EngineError("pairing_required","Connect and pair your local helper to start practising.",401)
    return engine.session(token)[0]


class PairingLimiter:
    def __init__(self):
        self.attempts=defaultdict(deque)
        self.lock=threading.Lock()

    def check(self, address):
        now=time.monotonic()
        with self.lock:
            for key in list(self.attempts):
                if not self.attempts[key] or now-self.attempts[key][-1] > 60:
                    del self.attempts[key]
            attempts=self.attempts[address]
            while attempts and now-attempts[0] > 60: attempts.popleft()
            if len(attempts) >= 8:
                raise EngineError("pairing_rate_limited","Too many pairing attempts. Wait one minute and try again.",429)
            attempts.append(now)


pairing_limiter=PairingLimiter()


def pair(request, pairing_code, engine):
    pairing_limiter.check(request.client.host if request.client else "local")
    expected=os.getenv("QUERYLAB_PAIRING_TOKEN", "")
    if not expected or not secrets.compare_digest(pairing_code.encode("utf-8"),expected.encode("utf-8")):
        raise EngineError("pairing_failed","The pairing code does not match your local helper.",401)
    return engine.session(create=True)[0]
