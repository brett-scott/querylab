# QueryLab PM scope and delivery status

## Active iteration: Google accounts and statistics

The user explicitly chose to skip the learner pilot because no testers are available, and requested accounts/statistics as the next work. Google sign-in is confirmed. Optional guest practice, Supabase authentication/progress storage, metadata-only tracking and a compact on-demand progress dialog are the engineering defaults for this iteration. The live site URL supplied by the user is https://brett-scott.github.io/querylab/.

Implemented locally: Google PKCE flow and callback at the existing Pages path; sign-out; private versioned attempt history and aggregate statistics; assistance tracking; idempotent cloud retries; account-bound pending sync and same-tab grading recovery. Database grants/RLS and its aggregate view protect each account's rows. The Pages workflow reads public configuration variables and rejects secret/service-role keys in the browser build. See the [activation guide and metric definitions](accounts-and-statistics.md).

Owner-side activation remains: create/configure the Supabase project and Google OAuth client, apply the migration, add public build variables and redeploy. No public project configuration has been supplied, so accounts remain disabled by default. The pilot is waived at the user's request; it is not a blocker to this iteration. Explicit helper expiry and broader browser-permission recovery remain separate unverified coverage, not completed pilot work.

Local verification: 8 unit tests passed; actual PostgreSQL ownership/RLS and aggregate checks passed; account-enabled browser suites passed at both root and project paths, including controlled OAuth responses and real SQL grading; guest Pages/helper suites also passed at both paths. The [account guide](accounts-and-statistics.md#verification-record) records exact evidence and limits. Google/Supabase were not activated remotely and the new GitHub workflow job has not been run on GitHub from this workspace.

The MVP history below retains earlier next-step recommendations; this active iteration supersedes references to a forthcoming pilot or continued deferral of accounts/statistics.

## GitHub Pages preparation — 18 October 2026

The static Vite website now supports repository subpaths, base-aware helper download/home links, and a GitHub Pages build/deployment workflow. The deployment reads the configured Pages URL, checks the helper package and browser navigation before publishing only the static build. Pull-request verification covers both root and `/querylab/` paths. See the [Pages setup guide](github-pages.md).

Local verification passed both builds and both two-test browser runs, including pairing, SQL, draft refresh and real-MySQL query/function/procedure grading at each path. The Windows archive passed independent integrity and credential-exclusion checks. Exact evidence and untested scope are recorded in the guide.

**User-confirmed hosted acceptance checks:** the user reports successful deployment and helper connection, followed by all four requested checks passing: run/submit a query, function and procedure; refresh with draft and connection recovery; disconnect and pair again; and another learner trying the downloaded helper from a fresh installation. These outcomes are user-reported and have not been independently observed by the agent. The deployment URL, browser and permission-prompt behavior were not supplied.

The proposed learner pilot was subsequently waived by the user; accounts/statistics are now the active post-MVP iteration above. Initial hosting planning remains five simultaneous learners with SQL execution on their own computers. Explicit expired-session recovery and browser permission allow/deny/recovery were outside the four reported checks and remain open; the fresh installation trial is user-confirmed.

## Current curriculum milestone ? 18 October 2026

All twelve exercises are implemented: six queries, three functions and three procedures across the two agreed datasets. The nine previously planned entries now have complete contracts, starters, three hints, explained references and executable grading across public and hidden fixtures. See [curriculum validation](curriculum-validation.md) for current evidence and limits.

The curriculum milestone supersedes the historical three-exercise status below. Static hosting and the four hosted acceptance checks above are user-confirmed, and the cost estimate reflects that architecture. The user has now waived the pilot and authorized the accounts/statistics iteration above. Explicit expiry and broader browser-permission recovery remain open coverage.

## Current helper milestone (supersedes delivery assumptions below)

**Windows download milestone:** implemented the requested standalone ZIP, guided native launcher and website Download Windows helper action. The package is generated with the site, excludes local credentials and needs Docker Desktop rather than a repository checkout or host Node/Python. The extracted runtime passed real pairing/SQL/grading/reset and restart-preservation checks. See [Windows guide](windows-helper.md), [download QA](helper-download-qa.md) and [validation](helper-validation.md). A clean-computer installation trial, interactive high-DPI/unsigned-file behavior and public HTTPS browser permissions remain release work.

**Focused UI milestone complete locally:** implemented the user-selected Focused Midnight Workbench. The layout emphasizes challenge overview and SQL, with collapsible requirements/results, on-demand schema and Focus mode. Both frontend builds passed; eight development/API/browser tests and four helper tests passed. [Focused UI QA](focused-ui-qa.md) and [design review](focused-ui-design-review.md) record evidence and limits. Helper browser-permission tests, installation/distribution trials, remaining nine challenges and the revised static-hosting estimate remain the next delivery work.

The user authorized a hosted static website connected to learner-local helper/MySQL. Local installation is now part of the learner journey; a shared hosted SQL service is no longer the delivery plan. Pairing, execution/grading, recoverable drafts, namespace-safe cleanup and public dataset SQL exports are implemented. See [helper validation](helper-validation.md) and [setup](local-helper.md).

The curriculum now contains twelve executable exercises. Next: trial setup against learner environments and validate a real HTTPS site and browser local-network permissions; helper distribution is implemented. Revise the earlier shared-stack cost estimate for static hosting. Accounts/statistics remain among the first post-MVP priorities. Earlier shared-server deployment/capacity requirements below are retained as historical review, not current release gates.

17 October 2026. Scope review against the confirmed [MVP decisions](../querylab-mvp-decisions.md), [challenge outlines](../querylab-mvp-challenges.md), [implementation plan](implementation-plan.md), [API contract](api-contract.md), README and available review/QA records. Final integration addendum: [validation report](validation-report.md) records 33 backend tests, seven API/browser tests and a ten-visitor smoke passing. This document is not public release approval; interim observations below are retained as review history and superseded by that report.

## Delivery assessment

The build remains aligned with the agreed initial three-exercise development milestone. It does **not** yet deliver the confirmed hosted MVP: twelve validated challenges across two datasets, accessible without accounts or local installation. Treat the runnable development stack as an intermediate deliverable, not a change to hosted delivery.

Implemented scope reported by the current source/documentation is the Midnight Workbench interface, real MySQL execution, schema inspection, results/errors, fresh-fixture submission, progressive hints, separate solution reveal, browser-local drafts, reset and anonymous execution lifecycle. OS-Q01, OS-F01 and OS-P01 are the three executable exercises. Nine library entries are explicitly planned; metadata and visible titles do not count as completed learning content.

## Evidence and unresolved validation

- QA records passing real-API checks for all three reference solutions, incorrect-query rejection, practice preservation through Submit, reset, cross-session access denial and database-level cancellation followed by successful execution.
- The recorded first integrated QA round was three passing and two failing tests. One failure was a corrected test-harness issue; the editor Escape/Tab behavior still required retest in that record.
- Source review identified stale expiry reporting, polling/cancellation recovery, missing refund NULL probes and an unbounded response-byte risk. Fixes and expanded checks are being integrated; do not count them as verified until final QA records their outcomes.
- Orchestration reports a successful frontend build and an earlier 28-test backend pass. Subsequent byte-limit/probe changes require affected checks again. Final integrated results supersede these interim observations.
- Public isolation, ten-learner capacity, deployment/recovery, broader browser/accessibility coverage and final expiry/cleanup evidence remain unverified in the reviewed records.

The final validation record must reconcile these items and state PASS/FAIL/UNTESTED explicitly. Screenshots support visual observations; they do not establish grading correctness or safe public execution.

## Scope changes and defaults

The confirmed decisions supersede the original local-only brief: hosted access is required; accounts, statistics, durable attempts/progress and standalone lessons are deferred. Browser-saved drafts remain required. These are authorized scope changes rather than omissions to silently reintroduce.

The refund procedure keeps the first slice within the online-store dataset; inventory stock transfer remains later curriculum. This is consistent with the current challenge outlines.

React/TypeScript, FastAPI, MySQL 8.4.9 and Compose are documented implementation choices. The one-hour inactivity lifetime, eight-second deadline, ten-session cap, row/SQL limits and single backend worker are engineering defaults, not proof of capacity or a production architecture. Validate resource limits and expiry behavior before hosting.

A separate free-practice sandbox is still **proposed** in D13 and is not implemented. Mutable challenge practice does not satisfy the proposed separate sandbox's isolation promise. Resolve whether it is included before calling the MVP scope complete; do not silently add it or mark it delivered.

## Original curriculum backlog ? completed 18 October

All nine now have executable fixtures, authored/verified grading, hints/explanations and negative/edge-case coverage:

| ID | Challenge |
| --- | --- |
| OS-Q02 | Monthly net-sales trend |
| OS-Q03 | Leading products in each category |
| OS-F02 | Customer net spending at a cutoff |
| BI-Q01 | Actionable replenishment list |
| BI-Q02 | Supplier delivery reliability |
| BI-Q03 | Stock movement ledger reconciliation |
| BI-F01 | Pack-sized replenishment quantities |
| BI-P01 | Atomic stock transfer |
| BI-P02 | Receive a delivery exactly once |

Completing these preserves the confirmed six-query, three-function, three-procedure allocation across online store and inventory. Do not expand to a third dataset, AI content or a larger library before this gate passes.

## Next sequence and release gates

1. **Finish validation of the three-exercise slice.** Retest all affected review fixes, keyboard behavior, expiry/recovery and response-byte limits. Publish final backend, build, API and browser outcomes with remaining limitations.
2. **Expand the remaining nine challenges.** Require deterministic fixtures, reference solutions, meaningful alternatives where applicable and deliberate incorrect-answer rejection for every shipped challenge. Validate inventory reset/isolation and preserve browser drafts across switching and reset.
3. **Validate public capacity and isolation.** Independently review shared MySQL permissions, routines, abuse controls, byte/memory limits, quotas, cancellation and cleanup; measure the ten-simultaneous-learner target, including hostile/wide/long-running workloads and recovery. A ten-session setting alone is not this evidence.
4. **Prepare and verify hosting.** Select a provider and production configuration only after the measured architecture fits the provisional A$150/month ceiling. Verify HTTPS/secure cookies, operational monitoring, recovery and the account-free hosted learner journey. No deployment or expenditure is represented as completed or authorized by this review.

Public access is blocked until the full validated curriculum and hosted isolation/capacity/operations gates pass. Keep the development stack private while those gates remain open. Trial participants, content review ownership, supported browser baseline and the proposed separate sandbox still need a clear recorded resolution before final MVP acceptance.
