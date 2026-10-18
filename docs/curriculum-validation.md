# Complete MVP curriculum

18 October 2026. All twelve challenges are executable in the existing workbench and local-helper architecture. No accounts or statistics were added.

| Added challenge | Executable focus |
| --- | --- |
| OS-Q02 | Six-month zero-filled net sales, cumulative sales and monthly growth |
| OS-Q03 | Top two dense revenue ranks per sale-time category, retaining ties |
| OS-F02 | Customer net spending at a supplied historical cutoff |
| BI-Q01 | Reservations, cutoff-aware inbound quantities and pack-sized replenishment |
| BI-Q02 | Batch-level supplier reliability, including late/missing deliveries |
| BI-Q03 | Stock-ledger closing balances and temporary shortages |
| BI-F01 | Pure reorder calculation with input validation and wide arithmetic |
| BI-P01 | Atomic transfers, reserved stock, linked ledger entries and stable retries |
| BI-P02 | Atomic multi-line receipts, cumulative allowances and exactly-once retries |

OS-Q01, OS-F01 and OS-P01 remain available, preserving the agreed six-query, three-function, three-procedure split. Every exercise has complete requirements, a starter, three progressive hints and an explicitly revealed explained solution. New content uses challenge version 1.1.0 so previously saved placeholder drafts do not replace the authored starters; drafts for the original three remain on their existing versions.

## Contracts and grading

Reports use explicit UTC boundaries rather than the current date. Routine requirements specify signatures, result columns, exact validation errors and validation precedence. Inventory reports distinguish receipt timestamps from present-day status. Replenishment floors each purchase-order line before aggregation and rounds whole-unit packs exactly. Receipt processing groups duplicate order lines before enforcing allowances, counts previous actual receipts beyond report cutoffs, and checks signed-INT stock/summary capacity with wide arithmetic.

Submit provisions a public fixture and two hidden variants under restricted execution users. Query comparisons require the documented aliases, values and row order. Routine checks compare responses, validation failures and all business tables after each call. Independent tests calculate report/function results separately from the SQL reference. Deliberately wrong submissions cover boundaries, missing months, ranking ties, receipt multiplicity, incorrect rounding, retry failures and missing transactions.

Procedure failure triggers deliberately interrupt writes after earlier changes. Correct procedures must roll back stock, audit records and operation metadata, then propagate the failure. Inventory comparisons preserve business identities while accepting different insertion orders and auto-increment gaps after rollback: transfers are matched by request key, linked movements by their complete business fields. Original unlinked movement identifiers remain checked. Top-level jobs are serialized per learner workspace; overlapping calls and caller-owned transactions remain outside these exercise contracts.

Public SQL exports include the expanded practice fixtures only. The Windows helper download is version 0.4.0 and includes all twelve challenges. Existing source installations need a helper rebuild/restart; previously downloaded helpers need the updated runtime. A helper restart expires anonymous sessions, so reconnect the website afterward. Browser drafts remain in the browser.

## Verification

- **Backend:** the final complete suite passed **188 tests** against MySQL 8.4.9 in 148.40 seconds. No tests were skipped. One existing Starlette/AnyIO deprecation warning remains. This includes the original 96 checks, 27 online expansion checks, 21 inventory reporting/function checks, 37 inventory procedure checks and seven SQLSTATE regressions.
- **Browser/API:** all eight development/API/browser tests passed; all six cross-origin helper tests passed, with no skipped tests or retries. The helper run submitted all twelve references and passed **456 grading checks**. Its slowest reference submission was 4,831 ms, within the existing eight-second deadline; this is a local measurement, not a public capacity claim.
- **Download:** the independently verified ZIP contains 28 allowlisted files, is 63,089 bytes, and has SHA-256 `652e3c7df7475d93afdd4af1909d0406f6b1bb58b1b255818e809f60bd2463e1`. Both preview sites serve this same artifact. All twelve graders also passed when imported from the extracted archive rather than the checkout.
- **Builds:** the development and helper-mode Docker frontend builds passed; both stacks are running with the expanded curriculum. ZIP integrity, manifest hash, standalone Compose and credential exclusion passed.
- **Evidence:** `qa/test-results.json`, `qa/helper-test-results.json`, `qa/screenshots/inventory-query-passing.png` and `qa/screenshots/inventory-procedure-passing.png`.

An initial browser run failed because the newly added test combined a labelled procedure and CALL without the starter's DELIMITER wrapper. The test was corrected to use the supplied client-script convention; the final full browser suite passed. Review also reproduced and fixed SQLSTATE comparison gaps, including multiple diagnostics after RESIGNAL. Seven focused real-MySQL regressions passed for those errors.

CI now also downloads the built artifact and runs `scripts/test-packaged-curriculum.py` against real MySQL. The equivalent local Compose command passed. The GitHub Actions workflow itself has not been run during this session.

## Release limits

This milestone completes the curriculum implementation. It does not represent a public deployment or a clean-computer installation certification. Public HTTPS-to-loopback browser permissions, learner installation trials and static hosting remain separate release work. Accounts and statistics remain post-MVP.
