# QueryLab: a quieter Midnight Workbench

17 October 2026. UI Designer review and user-selected design contract. The user approved the Focused Midnight mockup and requested implementation. Actual implementation evidence is recorded in [focused UI QA](focused-ui-qa.md) and the [design finish review](focused-ui-design-review.md); the static concept itself is not usability-test evidence.

## Evidence reviewed

- [Current paired workbench](../qa/screenshots/helper/paired-workbench-real-result.png).
- [Selected Midnight Workbench concept](../design/querylab-01-midnight-workbench.png) and its [UX notes](../design/querylab-ux-concept-notes.md).
- `frontend/src/App.tsx`, `frontend/src/styles.css`, and the authored OS-Q01 requirements in `backend/app/content/challenges.py`.

The user reports too much text and wants attention on the challenge and query window. The review supports simplifying visibility and hierarchy while retaining the charcoal/mint identity and complete SQL contracts.

## What currently competes for attention

The desktop screenshot displays the brief, editor, results and all eight schema tables at once. Schema columns and data types occupy an entire permanent rail, even when the learner is working on a known join. `SchemaExplorer` initializes every table expanded.

The brief combines metadata, tags, a long scenario, detailed numbered requirements, a hint introduction, a reveal button, a solution link and reassurance copy. Its scrolling requirements compete with a separate fixed guidance area, making the task look longer and more fragmented.

The center has a workbench heading, motto, local-environment label, file row, action row, execution explanation, editor status, results header and another footer. The global header and footer repeat the connection/environment information and add more mottos. Several interface labels are only 8–11px; reducing font size has made the screen busier rather than easier to scan.

The original concept already identified the density risk and recommended shallow, collapsible schema and fewer simultaneous scroll regions. The proposed revision follows that direction.

## Recommended concept: Midnight Workbench, focused

Default to two areas: a compact challenge panel and a substantially wider editor. Show supporting information when requested. Keep Run and Submit stable and immediately available, with genuine execution/recovery states visible when needed.

### Default visibility contract

| Area | Visible by default | Available on demand |
| --- | --- | --- |
| Header | QueryLab, Challenges, one labelled connection control | Connection details and workspace help |
| Challenge panel | Challenge ID/dataset, title, explicitly labelled Overview and short overview | Requirements (5), Expected output, hints and explained solution |
| Editor | File label, Schema and Focus controls, SQL, Run and Submit | Workspace menu containing Reset workspace and help |
| Results | Compact collapsed Results strip before the first execution | Full practice results or submission feedback after execution |
| Schema | A labelled Schema control | Dock with search, collapsed table names, expanded columns only for selected tables |
| Guidance | Hints button | Sequential hint disclosures; a separate deliberate explained-solution action inside More help |
| Persistence | A small truthful draft status | Explanation of browser-only storage in help |

The overview is explicitly a summary. The unchanged authored requirements remain the source of truth and can be opened before any SQL is written. `Requirements (5)` is a prominent, full-width disclosure directly below the overview, not hidden in a menu or tooltip. Count comes from the current challenge, not a hardcoded five. Expected output is a separate labelled disclosure next to the contract information. Neither opening nor closing these panels changes the SQL or execution state.

If learner testing shows the overview needs a few key constraints visible, these OS-Q01 summary statements are candidates. They are not shown in the first mockup and would not replace the detailed contract:

- Net spending at least 500.00.
- No completed orders in the 90-day window before the cutoff.
- Cutoff: 1 July 2026 UTC, exclusive.

The full Requirements disclosure retains exact interval boundaries, item-price calculation, refund status/timestamps, the fully refunded recent-order exception, eligible-order rules, grouping, output columns and sorting. Opening Expected output shows the authored four columns and required ordering. Do not change grading criteria to make the screen shorter. Functions and procedures likewise retain their full signatures, boundary behavior and error contracts.

### Layout and component foundation

- Preserve canvas `#111719`, panel `#151D1F`, primary text `#EDF4F2`, mint `#8AE6BD` and dark mint-button text `#102C23`. Use `#BAC8C4` for substantive secondary copy; reserve quieter tones for nonessential decoration.
- At 1600px, use a 56px header, about 340px challenge panel, 24px gutters and the remaining width for the editor. Avoid a permanent third column. Prefer 16px body text, 14px controls and SQL, and a 24px challenge title; keep metadata at least 12px.
- Use an 8px spacing base and modest 6–8px radii. Separate areas with fine borders and spacing rather than nested cards, gradients, pills or large shadows.
- Consolidate editor chrome into one compact header and one action row. Run stays outlined, Submit stays mint. Keep the existing shortcut behavior; show shortcut hints in accessible tooltips/help rather than adding a dedicated text row.
- Remove decorative workbench slogans, repeated dataset/footer lines and repeated healthy-connection statements from the work surface. One small draft status remains; storage failure must become a visible warning.
- Provide 44px interaction targets, a visible focus outline and labels for utility controls. These are acceptance requirements, not claims that a generated image passes accessibility checks.

### Interaction states

**Requirements and expected output:** expandable in place inside the challenge panel. Closing returns focus to the disclosure trigger. Reopening preserves reading position where practical. Long contracts scroll in the panel; avoid a second fixed guidance section competing for its height.

**Schema:** opens a 320px dock at the right on wide screens, leaving the editor usable. Start with table names collapsed, keep search and relationships available, and expose sample rows only after choosing a table. Download dataset SQL moves to a labelled dataset action inside this dock; setup instructions appear with the download action. Closing restores width and focus to Schema. On smaller desktops, use the support-panel behavior described below rather than compressing the editor into a narrow third column.

**Focus:** a labelled toggle hides the challenge panel and closes the schema dock; populated results remain available. A persistent Exit focus control and Challenge control make restoration obvious. Save the prior panel state and restore it on exit. Never remount or discard the editor draft. Focus mode does not dismiss errors, active execution, cancellation or connection recovery.

**Hints and solution:** Hints opens the optional guidance area and reveals only the requested hint. Preserve the three-stage sequence and its progress. More help contains Explained solution and workspace help. Revealing the complete solution retains the existing separate confirmation; never show solution text automatically after a failed submission.

**Before execution:** collapse the unused results body to a slim labelled strip. Avoid the existing large empty-state headline, paragraph, footnote and keyboard badge. The editor receives the recovered height.

**Run:** expand the results region automatically and retain `Practice results` plus `not graded`. Keep it around 25–30% of workspace height initially, with a collapse control and keyboard-usable resizing. Preserve previous output when collapsed and show row count in the strip. For multiple result sets, show the selector only when needed.

**Submit:** expand and select `Submission feedback`; keep it distinct from practice output. Show an explicit pass/fail summary with failed-check detail accessible. A practice result must never resemble a passed challenge.

**Busy and recovery:** Run/Submit disabled when workspace is preparing or a job is active; Cancel visible while executing. Connection unavailable, expired pairing, SQL errors and storage failure remain visible next to the affected action with a recovery control. Healthy connection detail stays quiet. Reset remains a labelled workspace-menu item with its existing confirmation and draft preservation.

### Responsive behavior

- At 1280px and wider, default to challenge + editor. Only open the third schema dock if the editor retains roughly 640px of useful width.
- Between about 900px and 1279px, use one support panel with labelled Challenge / Schema tabs next to the editor. Opening Schema switches support content rather than shrinking code into a third column. The active challenge title remains visible, and switching back restores the brief state.
- Below about 900px, use labelled Challenge / Editor / Schema views, retaining task context at the top. Default to Editor once a challenge is selected. Results stay below SQL and open after execution. Avoid a permanent narrow-screen advice banner; put screen-size advice in help.
- At mobile widths, use a compact header, wrapping task title and full-width disclosures. Keep Run, Submit and execution Cancel reachable; retain a labelled connection control. Do not shrink body copy to fit. Stack results below the editor with page scrolling when necessary.
- Check responsive rules at 200% zoom and with long routine definitions, error messages and table names. Information and recovery actions must remain available at every width.

## Finish gate for a later implementation

1. The default paired screen presents the challenge overview and SQL without an expanded schema or empty results card.
2. Full authored requirements and expected output are obvious and reachable with one action; all grading semantics remain unchanged.
3. A learner can open schema, preview rows, reveal one hint and return to SQL without losing their draft or cursor position.
4. Practice results, submission feedback, errors and cancellation remain distinct and visible when relevant.
5. Focus mode, disclosure toggles and connection recovery work by keyboard, with sensible focus restoration and screen-reader labels.
6. Verify WCAG AA text/control contrast, 200% zoom, mobile layouts and visible focus in the actual implementation. Contrast and usability are not certified by this review or a static mockup.

## Mockup composition

Create one front-on desktop concept of the default paired state, with no device frame. Keep the original charcoal/mint QueryLab identity. A slim header contains the brand, Challenges and a single connected control. A compact left challenge panel shows OS-Q01 / Online store, the actual title and a labelled short Overview, followed by prominent collapsed Requirements (5) and Expected output rows. A compact hint action and More help link sit below. Leave generous quiet space rather than filling the panel with extra teaching copy.

The wider right area contains the SQL editor as the dominant surface: query.sql, small labelled Schema and Focus controls, Run outlined and Submit mint, clear 14px monospace exploratory SQL, and a quiet draft-saved indicator. The editor extends almost to the bottom. Results are a collapsed bottom strip because the query has not run. No schema tree, sample data, revealed hints, solution, passing badge, stats, repeated local-environment labels or decorative mottos. Use the actual starter query or a clearly illustrative partial query; do not imply an incomplete draft solves the challenge. This image communicates hierarchy; the interaction states above define the handoff.
