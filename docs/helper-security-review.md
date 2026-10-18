# Local helper security review

17 October 2026. Independent, bounded source review of the browser-to-loopback helper change. Inspected `backend/app/helper.py`, `main.py`, namespace/lifecycle handling in `engine.py`, public SQL export, helper transport tests, frontend API/connection/workbench code, helper Compose, static Nginx configuration and setup/start scripts. No additional concrete blocker was identified in this inspection.

## Transport and pairing

- The helper checks Host against loopback names before routing. A remote hostname resolving to loopback does not satisfy this check.
- Exact configured Origin matching applies to GET, POST and OPTIONS, including status and pairing. Untrusted and opaque `null` origins are rejected. Requests without Origin remain available to local command-line clients; bearer authorization still applies to protected operations.
- Only status and pairing are unauthenticated API operations. Catalog, solutions, schema/sample reads, downloads, jobs and execution require a live bearer session. Cookies do not authorize helper operations.
- Pairing compares the configured secret in constant time and rate-limits attempts. The response contains a distinct session token, not database credentials. The frontend sends it in Authorization, omits cross-origin cookies, and stores it in session storage. The pairing code is cleared from the form after successful pairing.
- Preflight permits the intended methods and headers, reflects only the allowed origin, and can respond to the private-network request header. The previously identified HTTP 204 JSON-body defect was corrected to an empty `Response(status_code=204)` during this review. Browser QA must verify the integrated response.
- Frontend helper URLs accept HTTP loopback addresses only. The helper website build selects the static Nginx configuration, whose `/api/` location returns 404 rather than proxying execution through the hosted website.

## Personal MySQL preservation

- Helper mode requires a persistent installation namespace of exactly 12 lowercase hexadecimal characters. Cleanup selects complete schema/user identifiers matching that namespace and generated suffix lengths; it no longer uses the former broad `ql_` prefix.
- `destroy()` rejects foreign identifiers before connecting or issuing DROP statements. Startup compatibility checks run before cleanup; unrelated schemas, former development schemas and other installation namespaces are excluded.
- MySQL connection settings remain in the helper's local environment. There is no HTTP database-configuration endpoint. Status responses use safe connection/configuration messages rather than raw credential errors.
- Startup can retain an offline status while the API remains available for pairing. Later readiness checks serialize first initialization; subsequent checks do not erase active workspaces.
- SQL downloads are generated from authored public fixture variant zero. They contain no credentials, grants, hidden variants or DROP operations. They create a dedicated QueryLab database and explicitly instruct users to stop if it already exists.

## Evidence boundary

Reviewed tests include exact Origin policy across methods, unauthorized reads/cookie rejection, session/job ownership, DNS-rebinding Host rejection, preflight, safe status errors, offline startup, namespace guards and real-MySQL preservation of unrelated objects. These are source observations; this reviewer did not independently execute those suites. The final QA report owns test counts and runtime outcomes.

The actual connection from a publicly hosted HTTPS website to loopback HTTP, browser local-network permission prompts, and behavior across Chrome/Edge/Firefox/Safari remain unverified here. Local HTTP preview tests do not establish that cross-browser delivery path. This review is not a public deployment or browser-compatibility certification.
