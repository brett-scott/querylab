# QueryLab implementation API contract

Version 1 with helper protocol 1, 17 October 2026. Base path `/api`; JSON uses snake_case. Helper mode uses paired bearer sessions. Legacy same-origin development mode retains HttpOnly cookies. Browsers never receive database credentials. No account, progress-history or statistics API.

## Local-helper transport

`GET /` in helper mode serves a public HTML connection guide with a relative link to the safe status endpoint. It explains how to use the base address in the website's Helper URL field, contains no secrets and retains the helper's Origin/Host checks. It does not create or authorize a session. Outside helper mode it returns 404.

Enable `QUERYLAB_HELPER_MODE=true`, configure a persistent 12-character lowercase hexadecimal `QUERYLAB_WORKSPACE_NAMESPACE`, random `QUERYLAB_PAIRING_TOKEN` (at least 24 characters) and exact comma-separated `QUERYLAB_HELPER_ALLOWED_ORIGINS` without paths/trailing slashes. Bind to loopback. MySQL configuration is local environment only.

- Public `GET /helper/status`: `{mode:"helper",version:"0.2.0",protocol_version:1,requires_pairing:true,database:{connected:boolean,message:string,...}}`. Process liveness and database availability are distinct. Frontend rejects unsupported protocol versions before pairing.
- Public `POST /helper/pair`, JSON `{pairing_code:string}`: `{token:string,expires_at:string,ttl_seconds:number}`. Incorrect code: 401; more than eight attempts/minute/client address: 429. No cookies.
- Every other `/api/` request requires `Authorization: Bearer <token>`, including content/health. `POST /session` renews/reports the paired session with `created:false`.
- Explicit allowed-origin CORS for GET/POST/OPTIONS, authorization/content-type preflight and private-network permission header when requested. Disallowed Origins and non-loopback Host names are rejected. No-Origin requests still require bearer auth except status/pair.
- `GET /datasets/{online-store|inventory}/setup.sql`: `application/sql` attachment with public DDL/seeds for a new database. No destructive drops, user grants, answers or hidden fixtures; unknown dataset: 404.

Token storage is sessionStorage; drafts/helper URL use localStorage; pairing code is not persisted; fetch omits cookies. Restart/expiry requires re-pairing while preserving drafts. Execution waits for current-session schema initialization. Startup cleanup matches only complete installation-namespace schema/user names after compatibility validation; unrelated names remain untouched. This supersedes the dedicated-instance broad-cleanup wording below. See [setup](local-helper.md) for release limitations.

## Challenge content

- `GET /challenges` returns `{ "challenges": [ChallengeSummary] }`.
- `GET /challenges/{id}` returns `ChallengeDetail`.
- `GET /challenges/{id}/solution` returns `{ "sql": "...", "explanation": "..." }`, only requested after the learner explicitly chooses to reveal it.
- `GET /schema?challenge_id={id}` returns `{ "dataset": "online-store", "tables": [TableSchema], "relationships": [Relationship] }` describing the learner's practice schema. It must not read hidden grading fixtures.
- `GET /schema/sample?challenge_id={id}&table={name}` returns one result-set object with up to ten practice rows and a truncation indicator. Table names are validated against the selected practice schema; this endpoint never exposes hidden fixtures.

`ChallengeSummary` / `ChallengeDetail`: `id`, `title`, `dataset` (`online-store` or `inventory`), `dataset_name`, `type` (`query`, `function`, `procedure`), `difficulty`, `summary`, `scenario`, `objective`, `requirements: string[]`, `hints: string[]`, `starter_sql`, `expected_columns: string[]`, `ready: boolean`, `version: string`.

List and detail currently expose the same public shape. Hints contain three authored stages and may arrive together; the UI reveals one at a time. Routine signatures and prerequisites are stated in requirements/starter SQL. Do not include reference SQL, reference outputs or hidden fixtures. `ready=false` means the challenge is browseable but Run/Submit is not yet available; never present this as a completed challenge implementation.

`TableSchema`: `name`, `columns: [{name,type,nullable,key}]`, `row_count`. `key` is a string such as `PRI`, `MUL`, or empty. `Relationship`: `from_table`, `from_column`, `to_table`, `to_column`. Samples can be inspected with a learner-issued bounded SELECT against their practice schema. Display schema definitions are authoritative; generated design-image column names are illustrative.

## Session and execution

Run executes the supplied SQL string; the editor sends its highlighted text when present, otherwise the full draft. Submit sends the full draft. Separate top-level SELECT/WITH queries can begin on new lines without semicolons. Nested SELECTs, CTE bodies and main queries, UNION/INTERSECT/EXCEPT operands, comments, strings and WITH ROLLUP remain within their existing statements. Other statement types and routine bodies retain explicit separators; DELIMITER directives remain supported. A semicolon before a detached GROUP BY/WHERE/ORDER BY or similar clause returns a sql_policy error explaining the boundary before any script statements execute. Query submissions still require exactly one query, and all existing size/statement/result limits remain in force.

- `POST /session`, empty body: create/reuse anonymous session, return `{ "expires_at": "ISO8601 UTC", "created": true, "ttl_seconds": 3600 }` and set cookie. The server may provision lazily before Run/Submit/Reset as well. Renewed workspace expiry must be visible to the user.
- `POST /run`, body `{ "challenge_id": "OS-Q01", "sql": "..." }`: HTTP 202 `{ "job_id": "...", "status": "queued" }`.
- `POST /submit`, same body and response: grades on fresh independent fixtures, without mutating practice data.
- `GET /jobs/{id}`: returns `Job` below; only job-owning session may access.
- `POST /jobs/{id}/cancel`: request database-level cancellation, return the current `Job`. Only mark cancelled after execution is actually stopped.
- `POST /reset`, body `{ "challenge_id": "OS-Q01" }`: restore the selected dataset's practice schema, including learner routines/objects, HTTP 200 `{ "message": "Workspace reset.", "expires_at": "ISO8601 UTC" }`. Reject while a job is active. Retain browser editor drafts.

`Job`:

```json
{
  "job_id": "opaque-id",
  "status": "queued | running | completed | failed | cancelled",
  "result": {
    "mode": "run | submit",
    "result_sets": [{"columns": ["customer_id", "net_spend"], "rows": [[1,"525.00"]], "affected_rows": 0, "truncated": false}],
    "grading": {"passed": true, "checks": [{"name": "Visible fixture", "passed": true, "message": "Results match."}]},
    "elapsed_ms": 43
  },
  "error": null
}
```

`result` is null while queued/running and on failure; `grading` is omitted or null for Run. `result_sets` preserves multiple result sets; update-only statements may return an empty grid with `affected_rows`. JSON rows are arrays aligned with column order. Exact decimals are strings, SQL NULL is JSON null, dates/datetimes are ISO strings (UTC semantics). Query grades compare normalized values, required aliases, duplicate counts and documented ordering. Errors use `{ "code": "SQL_ERROR | TIMEOUT | CANCELLED | INFRASTRUCTURE_ERROR | ...", "message": "..." }`. Incorrect answers complete as completed jobs with `grading.passed=false`; infrastructure failures use failed jobs and must never claim an incorrect answer.

Run accepts whole scripts, including complete routine definitions. Support standard DELIMITER directives deliberately; never split compound routine bodies on every semicolon. State explicit transaction semantics in the runner documentation. One active job per anonymous session across tabs; retain one practice schema per dataset. Practice mutations persist until Reset or expiry. Submit uses disposable fixture schemas and execution users separate from the practice user. Hidden fixtures are present only inside the currently executing grader environment and never served through content/schema endpoints or error payloads.

## HTTP errors and limits

HTTP 401 session expired; 403 cross-origin operation; 404 unknown challenge or job inaccessible to the session; 409 session busy; 422 invalid request/SQL policy, oversize SQL or planned challenge; 429 service capacity; 503 database unavailable. Application errors follow `{ "error": { "code": "...", "message": "human-readable explanation" } }`; polling failures are recoverable UI errors, not a grading failure. Implementation error codes use lower snake_case, such as `sql_error`, `execution_timeout` and `session_expired`.

Initial engineering defaults: one-hour idle expiry, maximum 10 active anonymous sessions, one execution per session, four execution worker threads, 8-second SQL deadline, 500 displayed rows per result set, 32 KB script and 30 statement limits. Environment variables: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_ROOT_USER`, `MYSQL_ROOT_PASSWORD`, `QUERYLAB_COOKIE_SECURE`, `QUERYLAB_PUBLIC_ORIGIN`, `QUERYLAB_SESSION_TTL_SECONDS`, `QUERYLAB_MAX_SESSIONS`, `QUERYLAB_SQL_TIMEOUT_SECONDS`. Validate limits rather than claiming capacity from defaults. The frontend polls approximately every 400 ms while running and stops polling on unmount; cancellation remains an explicit server action. The server's 401 response is authoritative for expiry because API activity renews the idle lifetime.

Each Run uses a fresh connection with autocommit enabled; explicit transactions must begin and finish inside that one script. Uncommitted work is rolled back when the connection closes. Practice permits data manipulation and routine creation/removal; table/view/trigger DDL is not granted in this milestone. Reset recreates schemas and rotates execution credentials. API startup removes orphaned anonymous schemas/users from the dedicated instance. Run exactly one API worker; in-memory session/job ownership is not shared between processes.

Response data is streamed with a 1 MiB aggregate JSON budget across result sets and at most 256 columns per set. Row truncation stops the remaining script and closes its connection. Oversized responses return `result_limit`; grader snapshots additionally cap rows and bytes so excessive mutations cannot cause unbounded inspection. The selected MySQL deployment retains `max_allowed_packet=4M` because client memory cannot stream within one row packet.

Server-side isolation, request-origin checks, privilege boundaries, cancellation and expiry cleanup require evidence before public hosting. This contract does not certify MySQL shared-server execution as safe for public use.
