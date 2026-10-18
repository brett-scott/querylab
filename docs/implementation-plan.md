# QueryLab implementation plan and scope gates

## Authorized architecture update

The user also selected the [Focused Midnight Workbench revision](../design/querylab-04-focused-workbench.png) for implementation: compact overview, expandable full task rules, wider editor, on-demand Schema, collapsible Results and Focus mode. This supersedes the permanent expanded three-pane layout described below. Preserve all existing learning/helper behavior. Verification belongs in [focused UI QA](focused-ui-qa.md).

The user approved working toward a **hosted static frontend + local helper + learner-owned MySQL**. [Setup](local-helper.md) and [helper validation](helper-validation.md) describe the implemented milestone. The earlier shared hosted SQL architecture below is historical. Current release gates are reproducible local setup/pairing, safe namespace cleanup, real execution/grading, HTTPS-to-loopback browser permission/recovery tests, helper distribution and the remaining nine challenges. Public hosting, supported-browser certification and a revised static-hosting estimate remain open. Accounts/statistics stay deferred.

17 October 2026. Orchestration/PM handoff. Sources: [MVP decisions](../querylab-mvp-decisions.md), [challenge outlines](../querylab-mvp-challenges.md), [selected Midnight Workbench](../design/querylab-01-midnight-workbench.png), [API contract](api-contract.md).

## Scope

Build an account-free, real-MySQL practice application for intermediate SQL learners. Twelve authored challenges across online store and inventory: six queries, three functions, three procedures. Browser-local drafts survive refresh and Reset. Run modifies disposable practice data; Submit grades fresh fixtures independently; optional three-stage hints and separately revealed explained solutions. Charcoal/mint three-pane workbench with challenge navigation, brief, editor, results/feedback and schema explorer.

Public hosted delivery is the target, initially ten simultaneous learners under the provisional A$150/month ceiling. This implementation prepares locally runnable services and deployment documentation; public hosting requires credentials, a provider choice and measured safety/capacity gates. Do not substitute a static preview, mock SQL or SQLite for the learning loop. Accounts, statistics, standalone lessons, third dataset and durable progress remain out of scope.

## Ownership and handoffs

| Role | Responsibility | Gate evidence |
|---|---|---|
| Orchestrator / PM | Scope, API handshake, integration sequence, unresolved decisions | This plan and actual validation record |
| Backend engineering / curriculum | FastAPI, schemas/seeds, all 12 contracts/hints/solutions, runner/grader, anonymous isolation | Real MySQL reference/alternate/wrong-answer tests |
| UX architect / UI designer / frontend | Midnight design system, accessible workbench, API wiring, local drafts, execution/reset/hint states | Browser flows and screenshots |
| Integration / DevOps | Compose, environment, reproducible startup, limits and lifecycle | Health checks, startup logs, reset/cancel/expiry evidence |
| QA / independent reviewer | Acceptance checks, defects, retests and release assessment | Report with PASS/FAIL/UNTESTED, never implied certification |

Each developer owns their assigned files; do not revert peers' changes. Use the API contract before dependent implementation. Integrate independent backend/frontend work after the shared contract is agreed. Any material departure is documented with its impact; no need to ask learners to choose engineering details.

## Tasks and QA gates

1. **Foundation:** React/TypeScript/Vite, FastAPI, pinned MySQL 8.4 Compose, environment template and local startup instructions. Gate: reproducible package/build checks and MySQL/API readiness.
2. **Content contracts:** publish all 12 scenarios, precise schema/routine signatures, expected columns/errors, three hints and explanation. Finalize unresolved outline rules as explicit versioned engineering defaults. Gate: each reference runs on deterministic fixtures; no hidden assets/reference SQL in list/detail/schema payloads.
3. **Query vertical slice OS-Q01:** Run, results/errors, Submit on visible/hidden fixtures, restore Reset. Gate: correct reference and distinct alternative pass; plausible fan-out/refund/boundary errors and sample hard-coding fail.
4. **Function vertical slice OS-F01:** complete CREATE FUNCTION definitions, call examples, errors, independent boundary grading. Gate: thresholds, cents, NULL, negative input and non-mutation checks.
5. **Procedure vertical slice OS-P01:** routine definition/execution, response/state verification, atomic refund/idempotency. Gate: cumulative item/payment limits, retry/conflict, invalid inputs and injected failure rollback; practice unchanged by Submit.
6. **Execution lifecycle:** anonymous ownership, scoped users, one active session job, job polling/cancel, time/result bounds, expiry/cleanup. Gate: cross-session workspace/job denial; long-running SQL is stopped at database level and environment recovers; reset removes created objects and preserves editor drafts.
7. **Workbench integration:** challenge filters/library; scenario/rules; editor and keyboard actions; schema/sample inspection; all result sets, affected rows, truncation and grade feedback; progressive hints/solution; reset confirmation and busy/error states. Gate: representative query/function/procedure browser flows, refresh and challenge-switch draft recovery; desktop and narrow viewport inspection with screenshots.
8. **Expand remaining nine challenges:** inventory schema, all query/routine grading and content. Gate: per-challenge authored reference, alternatives where meaningful, wrong answer rejection and documented edge cases. Do not count a challenge as validated merely because its metadata renders.
9. **Final integration/release assessment:** rerun required build/unit/integration/browser checks after fixes. Document tested commands, screenshot paths, limitations and next tasks. Public readiness requires measured ten-learner load, abuse/privilege/isolation review and deployment verification; report unmet gates explicitly.

## QA loop and status

For each task: implementation -> scoped QA -> concrete defect feedback -> fix -> rerun failed/affected checks. Maximum three failed rounds before recording a blocker for that task and continuing independent work. Only mark validated after evidence passes. Final integration remains NEEDS WORK if a required gate is untested or fails. Inaccessible Docker/browser tooling is a limitation, never substitute fabricated evidence.

Current state: foundation and first three-exercise slice implemented and verified. See the [final validation report](validation-report.md): 33 backend tests, seven API/browser tests and a bounded ten-visitor smoke pass. Remaining nine challenge graders, separate sandbox scope and public hosting gates remain open.
