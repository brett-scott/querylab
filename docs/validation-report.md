# QueryLab first development milestone: validation

17 October 2026. **The first three-exercise milestone passes the checks below. The twelve-challenge public MVP is not complete or deployed.**

## Delivered

Midnight Workbench React/TypeScript interface; real MySQL 8.4.9 execution; anonymous, schema-scoped practice workspaces; async jobs and database cancellation; schema/sample inspection; separate practice results and grading feedback; progressive hints and explicit explained solutions; per-challenge browser drafts; full workspace reset.

Executable and graded: **OS-Q01**, **OS-F01**, **OS-P01**. The other nine library entries are visibly planned. Accounts, statistics and durable attempt histories remain deferred. Separate free-practice sandbox scope remains proposed.

The refund procedure updates a maintained payment-refund summary before inserting the refund, so an injected insert failure verifies genuine rollback of an earlier write.

## Evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Frontend TypeScript + production build | PASS | `npm run build`; same check also ran in the final frontend container build |
| Backend unit and real-MySQL integration | **33 passed**, 12.90 seconds | `QUERYLAB_INTEGRATION=1 python -m pytest tests -q -p no:cacheprovider` inside Compose with source mounted |
| API + Edge browser suite | **7 passed**, 27.4 seconds | `npm test` in `qa/`, actual local stack at port 8080 |
| Ten-visitor local mixed-workload smoke | **10/10 completed** | [Capacity report](capacity-smoke.md); three reference submissions + seven exploratory queries; eleventh session correctly receives 429 |
| Desktop and narrow-screen visual review | PASS for inspected screenshots | [Desktop](../qa/screenshots/responsive-desktop.png), [1024px](../qa/screenshots/responsive-tablet.png), [375px](../qa/screenshots/responsive-mobile.png) |
| Public deployment / hosted budget fit | NOT TESTED / NOT DEPLOYED | Provider and production configuration have not been selected |
| GitHub Actions run | NOT RUN | Workflow supplied in `.github/workflows/verify.yml`; equivalent local stack checks passed |

Backend evidence covers alternative correct queries, visible-answer hardcoding rejection, refund mistakes, routine signatures/boundaries, every NULL refund argument, sequential retries, payment/item budgets, injected rollback, cross-workspace grants denial, reset credential rotation, expiry cleanup, actual connection cancellation, 500-row truncation, response-byte/column caps and bounded grading snapshots. Expiry cleanup is tested through the engine with a controlled expired timestamp, not a one-hour browser wait.

Browser evidence covers the complete query learning loop; real function and procedure submissions; a function call returning GOLD; hints and deliberate solution disclosure; per-challenge draft restoration and reset focus; clearly disabled planned challenges; schema sample dialog; 1024px pane switching; 375px draft-indicator visibility; keyboard exit; unavailable browser storage; network-error draft retention; and cancellation recovery after an interrupted poll.

The network tests deliberately inject browser transport failures. The cancellation recovery test presents a nonterminal cancel response after sending the real server cancellation, then requires polling to recover and another real SQL query to succeed. These are controlled fault tests, not naturally observed outages.

## Review fixes verified

- Preserve the incoming port in the Nginx Host header so same-origin requests succeed.
- Use server expiry responses instead of an initial client deadline that contradicts sliding idle lifetime.
- Resume polling when cancellation returns before the worker terminates; retain failed-job error distinctions.
- Escape explicitly moves focus to the results tabs, including when autocomplete is present; Tab continues outside the editor.
- Let the editor shrink on narrow screens so draft status remains visible.
- Stream result rows with a 1 MiB aggregate response budget and a 256-column cap. Retain MySQL's 4 MiB packet setting for the per-row receive bound.
- Bound grader snapshots to 1,000 rows per authored table and 1 MiB total; reject excessive fixture mutations without unbounded memory allocation.

## Capacity interpretation

One local ten-visitor burst completed in approximately **3.03 seconds**, with wall-clock p50 **1.32 seconds** and p95 **3.03 seconds** across ten heterogeneous jobs. This is a small synthetic-fixture smoke with queue/polling time included. It is not a sustained-load test, an adversarial test, a hosting SLA or proof of budget fit. Deployment isolation, resource headroom and operational recovery remain release gates.

## Remaining work

Implement and validate the remaining nine challenges, resolve the separate sandbox decision, and establish content/trial ownership. Before public hosting, complete independent isolation/abuse review, measured sustained capacity on the chosen host, HTTPS/secure-cookie configuration and operational recovery. Broader browser, screen-reader and zoom coverage remain untested.

The local preview remains available at **http://localhost:8080**. Benchmark sessions were cleared afterward so the preview can accept a new learner. MySQL and the API have no published host ports. Startup and test instructions are in the root README.
