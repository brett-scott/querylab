# Focused Midnight Workbench: QA evidence

18 October update: the height slider has been replaced by a draggable divider. See [results divider verification](results-divider-qa.md) for the current interaction and checks. The original milestone evidence below is retained as history.

17 October 2026. EvidenceQA. This report covers the implemented interface served locally at `http://127.0.0.1:8080` and the paired static frontend at `http://127.0.0.1:8081`, using installed Microsoft Edge through Playwright and real local MySQL. It does not certify the complete public MVP.

## Specification and observed layout

The approved [design contract](ui-simplification-review.md) says: “Default to two areas: a compact challenge panel and a substantially wider editor.” It also requires: “Full authored requirements and expected output are obvious and reachable with one action.”

[Desktop default](../qa/screenshots/focused/desktop-default.png) shows the compact challenge overview beside the dominant SQL editor. Requirements and Expected output start collapsed; Schema is available from a labelled control; unused Results occupies a single strip. The charcoal panels, mint Submit, outlined Run and small draft status retain the selected design direction. Repeated slogans and the permanent schema rail are absent from this default screen.

[Full contract](../qa/screenshots/focused/full-contract.png) and [mobile challenge](../qa/screenshots/focused/mobile-challenge.png) show the expanded disclosures. Automated assertions compare all five OS-Q01 requirements and all four output columns with the actual challenge API response. Grading semantics are unchanged; the existing query, function and procedure reference submissions still pass real grading.

## Commands and recorded outcomes

Run inside `qa/` after starting the documented local services:

```powershell
npm.cmd exec playwright test -- --max-failures=1
npm.cmd exec playwright test -- --config=playwright.helper.config.js --max-failures=1
```

| Final suite | Result | Duration | Machine-readable evidence |
| --- | --- | --- | --- |
| Existing API/browser flows plus new focused regression | 8 passed; 0 failed, skipped or flaky | 43.5 seconds | `qa/test-results.json` |
| Cross-origin local-helper API/browser flows | 4 passed; 0 failed, skipped or flaky | 14.9 seconds | `qa/helper-test-results.json` |

The focused regression is in [focused.spec.js](../qa/tests/focused.spec.js). Existing meaningful coverage remains in [workbench.spec.js](../qa/tests/workbench.spec.js), [api.spec.js](../qa/tests/api.spec.js) and [helper.spec.js](../qa/tests/helper.spec.js). Helper screenshots mask pairing-code fields; helper traces, automatic screenshots and video remain disabled. Codes, tokens and database credentials are not printed by the tests.

Earlier adaptation runs exposed three test assumptions: treating a native summary as a button-role locator, focusing the desktop-only resize slider on a mobile layout, and querying the intentionally hidden editor by visible role while Schema was selected. The tests now select the labelled summary, test the resize slider on desktop, and verify the preserved SQL after restoring the visible editor. These were harness corrections, not reported application defects.

## Interaction evidence

| Scope | Assertions and actual screenshots | Result |
| --- | --- | --- |
| Requirements and output | Default hidden; Requirements opens/closes with Enter and retains focus; complete API-authored contract is present; disclosures survive Focus and pane changes. [Full contract](../qa/screenshots/focused/full-contract.png). | Pass |
| Schema | Eight table headings start collapsed. Search narrows to customers, expansion shows columns, Preview rows loads a real table. Escape returns focus to Preview rows; closing the dock returns focus to Schema. [Dock](../qa/screenshots/focused/schema-dock.png), [sample](../qa/screenshots/focused/schema-sample.png). | Pass |
| Focus and editor preservation | Challenge and schema disappear; Exit focus and Challenge remain available. Exit restores prior disclosures and schema. The original CodeMirror DOM remains connected; inserting text after the whole cycle lands at the original cursor offset of seven, proving cursor and SQL retention. [Focus](../qa/screenshots/focused/focus-editor.png). | Pass |
| Focus across responsive changes | Open schema at desktop, enter Focus, resize to 375px, then exit. Schema restores and its visible navigation button receives focus. SQL is unchanged when the editor is shown again. [Restored mobile Schema](../qa/screenshots/focused/mobile-focus-restored-schema.png). | Pass |
| Results | Initial strip collapsed. Real `SELECT 21 * 2` produces 42 and expands Practice results with a not-graded label. Collapsing/reopening preserves the output. Keyboard changes the desktop height slider; twenty real rows remain reachable at maximum 65% on a 1600 × 600 viewport. [Real result](../qa/screenshots/focused/real-results.png), [collapsed](../qa/screenshots/focused/results-collapsed.png), [short desktop](../qa/screenshots/focused/short-desktop-maximum-results.png). | Pass |
| Grading and guidance | Incorrect query fails, reference query/function/procedure submissions pass, and a real function returns GOLD. Two hints reveal sequentially without reading the solution; the solution requires its separate confirmation. Reset confirmation/Escape restores menu focus, Reset preserves SQL, and planned challenges cannot execute. [Passing query](../qa/screenshots/passing-submission.png), [hints](../qa/screenshots/progressive-hints.png). | Pass |
| Error and cancellation in Focus | Real SQL syntax failure remains visible in Focus. A deliberately interrupted polling request leaves Run disabled and Cancel available. Real cancellation reaches terminal state despite an injected nonterminal cancel response; subsequent real SQL returns 123. [SQL error](../qa/screenshots/focused/focus-sql-error.png), [polling error](../qa/screenshots/polling-error-busy.png), [recovered query](../qa/screenshots/cancelled-polling-recovery.png). | Pass |
| Helper compatibility | Exact-origin/CORS/Bearer enforcement, pairing, real 42, real passing grade, SQL download inside the newly opened schema dock, refresh/disconnect draft retention, and invalid-token recovery while in Focus all pass. Run and Submit stay disabled during delayed schema preparation. [Helper grading](../qa/screenshots/helper/paired-grading-pass.png), [recovery](../qa/screenshots/helper/invalid-bearer-recovery.png). | Pass |
| Storage/network errors | Injected browser-storage failure displays an unsaved warning and never claims Draft saved. An aborted Run request shows a connection error and preserves SQL. | Pass |

## Responsive and visual inspection

Screenshots were actually opened and inspected, not inferred from passing tests. The reviewed set includes the desktop default, full contract, schema dock/sample, Focus, real/collapsed results, SQL error in Focus, maximum-height short-desktop results, tablet Schema, mobile Editor/Challenge/Schema, mobile Focus restoration and narrow reflow.

- At 1600 × 1000 the challenge/editor hierarchy matches the selected mockup, with generous code space and optional supporting content.
- At 1024 × 1000, [Schema replaces the support panel](../qa/screenshots/focused/tablet-schema.png), while the challenge ID/title stays visible above it. Challenge restores the existing disclosure state.
- At 375 × 667, [labelled pane controls](../qa/screenshots/focused/mobile-editor.png) stay visible and Run/Submit remain reachable. The [full challenge](../qa/screenshots/focused/mobile-challenge.png) uses vertical page scrolling; [Schema](../qa/screenshots/focused/mobile-schema.png) uses the available width. Horizontal document overflow assertions pass.
- At 800 × 500, [reflow evidence](../qa/screenshots/focused/zoom-equivalent-reflow.png) shows stacked editor/results. The last real output row and execution controls are reachable by scrolling even after the desktop Results height was set to 65%. This is equivalent CSS-viewport reflow coverage for a 1600 × 1000 window at 200%; it is **not actual browser-zoom testing**.

The desktop screenshot used for visual comparison runs the same workbench component as the helper frontend; the helper suite separately verifies the labelled Connection control, pairing and local execution.

## Findings and limits

No reproducible blocking defect remains in the tested flows. Two implementation edge cases identified during review—missing challenge identity while tablet Schema is open, and keyboard focus landing on a hidden editor control after exiting Focus at a narrower width—were corrected and are covered by the final passing regression and screenshots.

Design level: **Good** for the requested simpler workbench. This assessment refers to hierarchy, disclosure behavior and responsive evidence above; it is not an accessibility or production certification. The agreed implementation flows pass. Public-release readiness is **not determined** by this UI check.

Not tested here: actual browser zoom, a complete WCAG contrast/control audit, screen readers, Firefox/Safari, real mobile hardware, a deployed HTTPS site's localhost permissions, and user usability sessions. QueryLab remains a single dark-theme design; a theme switch was not part of the approved specification. The previously recorded helper installation, public HTTPS/local-helper testing and nine remaining challenges remain separate backlog work.
