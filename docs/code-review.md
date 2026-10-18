# First milestone code review

17 October 2026. Independent source review of the initial executable query, function and procedure slice. Inspected `backend/app/engine.py`, `main.py`, `sql.py`, authored solutions/contracts, integration tests, frontend workbench/API/editor/results, Compose and Nginx configuration. This review did not run the application or tests; execution evidence belongs to QA.

The privilege boundaries are deliberately scoped: learner SQL uses generated database users, grading routines execute under restricted users, and table inspection does not invoke learner routines with control credentials. Practice and disposable grading schemas are separate. Hidden-fixture SQL errors are replaced by generic feedback. Compose exposes only the frontend on loopback. These are useful controls, not public deployment certification.

## Findings sent to owners

1. **Must fix: active workspace incorrectly reported expired.** `App.tsx` scheduled expiry from the first session response, while `Engine.session()` extends the server expiry on authenticated activity. A learner still working after the original hour would lose editor actions and see an inaccurate expiry notice. Starting fresh could reuse the same live workspace. Root accepted the finding and is removing the stale client deadline, relying on authoritative server 401 responses and describing inactivity expiry accurately. Retest after integration.

2. **Must fix: cancellation cannot recover after a failed poll.** The polling error path retains the running job and stops polling. If the subsequent cancel request returns a nonterminal status, the original cancellation handler never resumes polling, leaving the workspace permanently busy. Root accepted the finding and is adding nonterminal polling recovery and terminal error handling. Retest a failed GET followed by a nonterminal cancel response, then terminal cancellation/failure.

3. **Should fix: refund grading omits three required NULL cases.** `refund_probes()` checked NULL request key and timestamp but omitted NULL item ID, payment ID and amount. A submission could return the wrong error for these published inputs and still pass. Sent to backend owner for three explicit probes. Reference solution already validates these inputs; verify amended grading against a deliberately incomplete implementation as well.

## Remaining public release gate

**Must fix before public access: row bounds do not bound response bytes.** `execute()` fetches up to 501 rows into memory and then builds JSON representations. Wide cells can consume substantial memory within that row count; MySQL's packet limit is not an aggregate response budget. Add a cumulative byte/cell budget, stop server work when exceeded, and test recovery under concurrent wide-result queries. This is recorded as a release-gate issue within the existing resource/isolation review, not a claim that the local milestone has been stress tested.

The implementation also correctly documents pending independent isolation review, anonymous abuse controls, HTTPS/secure cookies, measured ten-learner capacity and operational recovery. None were certified by this source review. Nine planned challenge entries remain outside the executable slice.

## Handoff

Final integration update: the expiry/cancellation fixes, all NULL refund probes, aggregate response limits and bounded grading snapshots are implemented. The [validation report](validation-report.md) records 33 passing backend tests and seven passing API/browser tests, including poll-failure cancellation recovery. The release-gate concerns remain about public deployment and broader stress/isolation evidence, not unresolved versions of those local defects.

The two frontend fixes and expanded refund probes require final QA against the integrated build. Consult the final validation report for their actual outcomes; accepted fixes in progress are not passing test results. No additional control-credential execution escape was identified in the bounded source inspection.
