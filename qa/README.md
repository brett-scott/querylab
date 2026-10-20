# QueryLab independent evidence QA

The account iteration adds `playwright.accounts.config.js`. Its Google/REST responses are controlled fixtures; its opt-in SQL flow uses real MySQL through a development helper. It checks PKCE callback paths, account ownership, sync retry/idempotency, assistance across refresh, and refresh during grading. `node scripts/test-progress-database.mjs` from the repository root separately checks actual PostgreSQL row security and aggregates in an isolated container. See the [account guide](../docs/accounts-and-statistics.md) for configuration and honest coverage limits. The original development suite excludes the account-specific tests.

For GitHub Pages, run `npx playwright test --config playwright.pages.config.js --grep 'static Pages build'` after building the helper-mode frontend with the same `QUERYLAB_BASE_PATH`. This suite owns its preview on port 5173 and checks both root and project-path builds in CI. Set `QUERYLAB_PAGES_WITH_HELPER=1` and run the complete Pages suite to additionally pair with a development helper and grade a query, function and procedure against real MySQL. It reads ignored `.env.helper` internally and disables traces/screenshots. See the [Pages guide](../docs/github-pages.md) for commands and validation limits. The normal development suite excludes these dedicated Pages tests.

The focused layout adds `tests/focused.spec.js` to the original suite. Run `npm test` for the eight development-mode tests and `npx playwright test --config playwright.helper.config.js` for the four helper tests. The [focused UI report](../docs/focused-ui-qa.md) supersedes older layout observations below and records actual new-build results, screenshots and coverage limits.

For the preferred local-helper architecture, start `../scripts/start-helper.ps1 -Preview` from the repository root, then run `npx playwright test --config playwright.helper.config.js` inside `qa/`. See [helper QA](../docs/helper-qa.md) for the four passing tests and privacy precautions. Restart the helper between repeated full runs to clear temporary sessions/pairing limits. The original seven-test same-origin suite below remains a compatibility check.

The tests exercise the locally served application at `http://127.0.0.1:8080` against real MySQL. They use the installed Microsoft Edge browser through Playwright; no fake SQL engine is used. Public deployment and ten-learner capacity are separate release gates.

## Run

Start the Compose application first, then:

```powershell
cd qa
npm ci --cache ../.npm-cache
npm test
```

Optional focused runs: `npm run test:api` and `npm run test:ui`. Set `QUERYLAB_URL` to test a different same-origin application URL. Playwright uses one worker to keep execution deterministic. These tests create anonymous sessions and mutate their own isolated practice data; restart the backend between repeated full runs if the ten-session cap is reached. Never run these against a public service with unrelated learners.

Windows defaults to installed Edge. Other systems use Playwright's Chromium installation; `QUERYLAB_BROWSER_CHANNEL` can override the selected channel.

## Evidence

`test-results.json` records actual Playwright results. `screenshots/` stores deliberate desktop, tablet and narrow viewport captures, samples, hints, solution disclosure, submissions, connection and storage failures. `test-artifacts/` stores failure traces/screenshots and API outcome attachments locally. Screenshots prove appearance; assertions and API outcomes establish behavior.

Connection and polling interruption tests deliberately abort selected browser requests. The polling-recovery test sends a real cancellation to the backend but presents its response to the browser as still running, then requires real polling to recover the terminal state and a fresh SQL query to succeed. This is fault-injection evidence, not an observation of naturally occurring network loss.

## Current validation

Final integrated round on 17 October 2026: **7 passed in 27.4 seconds** against the real local MySQL stack and installed Edge. Earlier test-harness issues and the editor focus/mobile clipping defects have been corrected and retested. Escape now explicitly moves focus to the results tabs; Tab continues through controls.

The expanded second round recorded **5 passed, 2 failed**. The complete query browser flow now passes, including independent grading, deliberate solution disclosure, versioned drafts, Reset preservation and dialog focus restoration. Simulated polling failure followed by a real cancellation also recovers correctly. Escape/Tab still fails. The routine browser test passed function Submit, then stopped on a second QA harness issue: appending SELECT to a raw CREATE FUNCTION reference without a terminating delimiter. The script is now correctly wrapped in DELIMITER directives for retest. Narrow screenshot inspection additionally found that the editor's draft indicator is clipped at 375 × 667; this has been sent to the frontend owner with a viewport regression assertion.

An earlier matching-origin POST failed with HTTP 403 because Nginx stripped the forwarded port from Host. The integration owner fixed the proxy; the subsequent real-API round passed using `Origin: http://127.0.0.1:8080`.

Actual passing API assertions: catalog has twelve challenges and exactly three executable entries; integer/decimal/NULL result values; HttpOnly anonymous cookie; inaccessible other-session job; denied cross-workspace database read; incorrect query rejected by grading; all three reference solutions pass; practice mutation survives Submit and is restored by Reset; `mysql.user` blocked by SQL policy; syntax error distinguished from incorrect answer; active-job busy protection; infinite stored-procedure cancellation reaches confirmed cancelled state; subsequent SQL succeeds; Reset removes the learner procedure.

Desktop, 1024px and 375px screenshots have been visually inspected. The built workspace uses the selected charcoal/mint direction, three desktop panes, an outlined Run action, mint Submit, syntax colors and separate results/feedback. At 1024px the schema has a separate control; at 375px pane switching and the browser draft indicator remain available. The browser suite also passes real function/procedure submissions, a GOLD function return, complete query flow, reset focus, planned-content gating, browser-storage failures and interrupted-poll cancellation recovery.

Assessment: **first milestone passes the tested flows; public MVP remains incomplete**. Nine curriculum entries remain visibly planned. The separate [ten-visitor smoke](../docs/capacity-smoke.md) passes one short local mixed-workload burst; public sustained capacity, abuse controls, screen-reader behavior, zoom and other browsers remain unproven. The [validation report](../docs/validation-report.md) records 33 passing real-MySQL backend tests, including controlled expiry/cleanup; a one-hour browser wait was not performed.
