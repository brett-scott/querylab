# Focused workbench design contract and finish gate

17 October 2026. Independent implementation review of the user-approved [Focused Midnight Workbench](../design/querylab-04-focused-workbench.png), using the [designer's interaction contract](ui-simplification-review.md). Evidence below comes from the rebuilt site, not the previous preview.

## Product lens

Intermediate SQL learners are reading a business challenge, writing a query or routine, checking practice output, then submitting for grading. The challenge contract and editable SQL must remain easy to reach; supporting schema, hints and solutions should consume space only when requested. QueryLab's charcoal/mint identity, real local-helper execution, browser drafts and distinct practice/grading states are existing constraints. The user approved less simultaneous text, not reduced challenge semantics.

## Design contract

**User + job:** Intermediate learner solves a realistic SQL challenge without losing their draft or place.

**First-read object:** The active challenge overview beside editable SQL.

**Primary action:** Run the current SQL; Submit deliberately requests grading.

**Density decision:** Quiet default, compact controls and readable supporting information disclosed on demand. A wide editor earns the space reclaimed from schema and unused results.

**Hierarchy:** Challenge title and labelled overview; conspicuous Requirements and Expected output; SQL; stable execution controls; optional schema/help; output when relevant.

**Interaction model:** Two-pane editing workspace on desktop. Schema docks only when width permits; smaller screens switch labelled support views. Focus hides support without hiding errors or execution recovery, and restores the prior workspace.

**Responsive priority:** Preserve readable SQL, task identity and execution controls. Mobile uses labelled Challenge/Editor/Schema views rather than compressed three-column desktop content.

**References:** The approved QueryLab image is the visual authority. Adjacent product patterns below explain the interaction choices; they are not alternate designs.

- [VS Code Zen Mode](https://code.visualstudio.com/docs/editing/getting-started/userinterface#_zen-mode): remove peripheral tools while editing and expose a way back. QueryLab keeps execution and recovery controls because learners must still run and inspect SQL.
- [DataGrip tool windows](https://www.jetbrains.com/help/datagrip/tool-windows.html): supporting tools can be shown, hidden and docked. Transfer that optionality to schema instead of permanently reserving a third column.
- [DataGrip query results](https://www.jetbrains.com/help/datagrip/viewing-query-results.html): results are an execution-specific work surface. QueryLab reveals output after Run and separately labels submission feedback; it does not imply that practice output is a passing grade.

**Forbidden defaults:** Marketing hero; account/statistics dashboard; decorative gradients or glass; permanent expanded schema tree; large pre-execution empty-state card; repeated environment labels/mottos; tiny copy used to fit more text; hidden or shortened grading requirements.

**Finish evidence:** New-build desktop 1600px, tablet 1024px and mobile 375px screenshots; focused editor; expanded schema and results; QA checks for disclosures, hints, draft preservation, keyboard controls and recovery. Do not claim contrast, assistive-technology or zoom certification without measured evidence.

## Required observable outcomes

1. Default desktop shows short labelled overview, collapsed Requirements/Expected output, dominant editor, collapsed results and no schema tree.
2. Full unchanged rules and expected output are reachable in one action; no hidden grading semantics are replaced by the overview.
3. Schema, hints, results and focus changes retain SQL. Focus can be exited and prior panels restored.
4. Run and Submit remain distinct and reachable. Practice output is explicitly ungraded; submission feedback, errors and cancellation remain visible when relevant.
5. Desktop, tablet and mobile retain useful editor width, readable controls and labelled task/schema access without page-level horizontal overflow.
6. The existing charcoal/mint palette and restrained borders remain; additional text appears because the learner requested it or a real state needs action.

## Finish gate

**Decision: PASS — the tested workbench states meet the approved simplification contract.**

This is a bounded visual/product-design gate. The final dedicated focused-workbench browser test and four helper tests passed according to QA; the remaining legacy flow rerun was still running when this review was finalized. See the [QA report](focused-ui-qa.md) for final execution results.

### Evidence inspected

- [Desktop default, 1600px](../qa/screenshots/focused/desktop-default.png): labelled overview beside a dominant editor; Requirements and Expected output are prominent collapsed controls. Schema is absent and results use one slim strip. This matches the approved image's information hierarchy.
- [Expanded contract](../qa/screenshots/focused/full-contract.png): all five business rules remain readable on demand. [Mobile contract](../qa/screenshots/focused/mobile-challenge.png) shows the complete rules and four output columns without page-width compression.
- [Schema dock](../qa/screenshots/focused/schema-dock.png): optional right dock leaves a useful editor on a wide desktop. [Focus](../qa/screenshots/focused/focus-editor.png) exposes Challenge and Exit focus while retaining execution controls.
- [Practice output](../qa/screenshots/focused/real-results.png) explicitly says not graded. [Focused SQL error](../qa/screenshots/focused/focus-sql-error.png) remains visible beside a preserved draft. [Short desktop/max results](../qa/screenshots/focused/short-desktop-maximum-results.png) shows the last result row reachable after scrolling.
- [Tablet schema, 1024px](../qa/screenshots/focused/tablet-schema.png): support tabs switch without reserving a third column. The final capture now retains OS-Q01 and the active challenge title above the tabs. [Tablet challenge](../qa/screenshots/focused/tablet-challenge.png) retains the same context when returning to the contract.
- [Mobile editor, 375px](../qa/screenshots/focused/mobile-editor.png) and [schema](../qa/screenshots/focused/mobile-schema.png): labelled views retain task context; controls remain readable and result tables stay inside their surface.

### Findings resolved and verified

1. The first tablet build lost challenge identity when Schema replaced the brief. The rebuilt 1024px captures above show a compact persistent ID/title and a useful editor; this HOLD is closed.
2. [Focus restored at 375px](../qa/screenshots/focused/mobile-focus-restored-schema.png) shows the schema returned after desktop Focus, resize, and Exit focus; the visible Schema navigation control receives keyboard focus. QA reports the dedicated restoration assertion passed.
3. [800px reflow](../qa/screenshots/focused/zoom-equivalent-reflow.png) shows readable controls, the retained draft and the last result row reachable with page scrolling. This tests a narrow CSS viewport, not actual browser zoom.

No required visual findings remain in the inspected states. Source review also caught and the frontend corrected an old export-action sizing override, inactive tablet support selection and short-desktop results clipping; the final captures show selected support tabs and reachable result tails.

### Keep

The SQL work surface now earns most of the first viewport. Mint Submit remains distinct from outlined Run; full contracts are conspicuous rather than silently abbreviated. Optional schema/help and the small unused-results strip materially reduce simultaneous text. Preserve those choices.

### Scope limits

Root measured selected solid CSS text/background color pairs: body 15.34:1, secondary 9.90:1, metadata 7.82:1, primary button 10.05:1, Run 11.78:1, warning 8.76:1, SQL comments 5.75:1. These source-pair checks exceed 4.5:1; they do not certify every rendered state, control boundary, disabled element or overall WCAG conformance. Screen-reader and browser-zoom certification are not claimed by this screenshot review.
