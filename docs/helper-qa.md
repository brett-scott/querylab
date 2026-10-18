# Local helper evidence QA

## Scope and execution

Requirement: “Can we work towards this kind of setup as you suggested with the helper approach”. The intended flow keeps the website's editor, connects to a learner-local helper, runs and grades SQL locally, and provides practice dataset setup SQL. Credentials stay in local configuration. Existing same-origin mode remains separately tested.

Run the documented helper stack first, then from `qa`:

```powershell
npx playwright test --config playwright.helper.config.js
```

The default site is `http://127.0.0.1:8081`, and the separate helper API is `http://127.0.0.1:8765`. Override with `QUERYLAB_HELPER_SITE_URL` and `QUERYLAB_HELPER_API_URL` if needed, and configure the matching exact allowed origin in the helper. Tests read the private pairing code from the local ignored `.env.helper` directly in the Node process. They never print it, write tokens to attachments, or enable traces/videos. Manual screenshots mask the pairing input.

`qa/helper-test-results.json` contains recorded results; `qa/screenshots/helper/` contains deliberate captures. Screenshot appearance is paired with browser/API assertions. The test run creates several helper sessions; avoid unrelated learner sessions while running it.

## Tested scope

- Exact-origin GET/POST denial, allowed/denied preflight, unauthenticated denial, bad pairing code rejection, bearer-protected catalog and session renewal, and no helper cookies.
- Browser pairing across separate ports, real SQL returning 42, reference query grading, dataset download with public DDL/seed and no destructive statements, user creation or hidden fixtures.
- Per-tab bearer storage, no pairing/database secrets or bearer in localStorage, browser refresh and disconnect preserving drafts.
- Invalid bearer during Run and startup recovers to pairing and executes again after reconnection.
- Remote helper URL validation before any outbound request, simulated unreachable-helper messaging, and narrow-screen setup screenshots.

## Actual results

17 October 2026, real MySQL 8.4 helper on port 8765 and static frontend on 8081, installed Edge through Playwright:

- First round: **2 passed, 2 failed in 14.9 seconds**. Full browser SQL/grading/download/draft flow and narrow setup validation passed. API sequencing found a real protocol defect: a JSON body was sent with HTTP 204 preflight, resetting the reused connection. The backend owner replaced it with an empty response. Recovery initially stopped at an ambiguous QA selector; the test now scopes the pairing action to its form.
- Second round: **3 passed, 1 failed in 29.6 seconds**. Exact-origin API/preflight/auth checks passed, as did the complete browser flow and mobile setup/network-failure assertions. Recovery retained the draft and paired successfully, but its immediate Run failed with “Finish or cancel the active operation before starting another.” The newly paired schema request held the session operation lock while Run was already enabled. The frontend owner gated execution on schema readiness for the current session and revision.
- Final integrated round: **4 passed in 16.0 seconds**, exit code 0. The recovery regression deliberately holds the real schema response after re-pairing, asserts the preparation notice and disabled Run/Submit controls, releases the response, then requires an immediate real Run returning 123. Startup with an invalid bearer also recovers through pairing without losing the draft. No sleep-based workaround is used.

Visually reviewed `connection-desktop.png`, `paired-workbench-real-result.png`, `connection-mobile.png`, `connection-mobile-form.png`, `paired-connection-status.png`, `invalid-bearer-recovery.png`, `recovery-preparing-workspace.png`, `recovery-run-outcome.png`, and `paired-grading-pass.png`. They show the charcoal/mint interface, a centered setup card with labelled URL/password fields, and the three-pane desktop workbench with real results of 42 and 123. Narrow setup uses an inner scrolling pane; assertions establish that the pairing input and Check connection action are in the viewport after scrolling. The preparation capture shows disabled SQL actions while the editor draft remains visible; the grading capture shows passing practice and unseen-fixture checks. Pairing fields are deliberately masked in screenshots.

Status: **PASS for the tested local integration scope**. Both reproducible product defects found during QA (HTTP 204 response body and Run/re-pair initialization race) were fixed and retested. No unresolved reproducible defect remains in these four tested flows. Public-browser release readiness remains **NOT DETERMINED**, independent of the local integration result.

## Coverage limits

The final [helper validation](helper-validation.md) records the separate backend evidence: 89 passing tests, real imports of both SQL exports, preservation of unrelated/other-namespace database objects, and a separate helper connected to the existing development MySQL. Those checks complement the browser scope below; learner-host MySQL networking still needs trials.

Local HTTP on different ports establishes cross-origin browser behavior. It does not prove a deployed HTTPS website can contact localhost under every browser's local-network access, mixed-content and permissions policies. That needs a real approved HTTPS origin and target-browser testing. Expired-session UI is tested with invalid bearer fault injection; idle timeout and backend cleanup require separate backend assertions. MySQL 8.4 compatibility, external-server setup and safe namespace cleanup require backend/packaging tests. Database import correctness requires executing exported SQL against a fresh MySQL schema rather than only inspecting download contents. No public deployment or universal browser certification follows from these tests.

The supplied `qa-playwright-capture.sh`, `ai/agents/qa.md`, and `public/qa-screenshots/test-results.json` are absent from this repository. Existing React components and the repository's Playwright/Edge pattern are used for evidence instead.
