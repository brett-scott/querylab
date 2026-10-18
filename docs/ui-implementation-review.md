# Midnight Workbench implementation review

17 October 2026. UX architecture / UI design review. Source: [selected concept](../design/querylab-01-midnight-workbench.png), [design direction](../design/querylab-concept-directions.md), [API contract](api-contract.md).

## Acceptance contract

- Preserve the selected charcoal/mint workbench: brief and requirements left, editor/results central, schema right. Mint identifies the main Submit action; Run remains outlined and Reset secondary. Avoid a marketing landing page or dashboard.
- Keep the challenge title, business exception, cutoff and complete expected-output contract accessible while writing. Use authored schema definitions rather than incidental text in the concept image.
- Distinguish the three executable initial challenges from the nine planned challenges in the library and workspace. Planned content must not permit Run/Submit or imply validated grading.
- State that Run operates on mutable practice data, while Submit uses independent fresh tests. Practice results always say not graded; grading failures and infrastructure failures have different wording.
- Preserve drafts per challenge and content version. Confirm browser storage success before claiming a draft is saved; provide an accurate fallback when storage is unavailable. Reset never clears the draft.
- Provide queued/running, cancellation requested, confirmed cancellation, SQL error, capacity busy and expired/recreated workspace states. Disable conflicting actions while work is active; a failed poll must not imply the server stopped executing.
- Reset confirmation identifies the dataset and removal of practice mutations/routines. Explained-solution disclosure is separate from progressive hints and requires deliberate action.
- Use the selected Midnight Workbench dark theme. Light/system theme selection is not committed MVP scope; if added later, ensure editor colors remain readable against the surrounding surfaces.
- At 1024px, preserve useful editor width by moving schema behind an accessible control. At narrower widths, show an explicit supported-width notice without hiding drafts or destructive recovery controls. Validate zoom independently of viewport width.
- Use semantic headings, labelled controls, native modal focus management, visible focus, keyboard-accessible schema/results scrolling and live status announcements. Explain how to leave the Tab-indenting editor using Escape then Tab. Do not use color as the only grading/error cue.

## Source review findings

Initial review inspected `Dialog.tsx`, `SqlEditor.tsx`, `ResultsTable.tsx` and `api.ts` while the workbench implementation was being written. Native dialog focus restoration and result table headers/caption were present. These are source observations, not browser-tested results.

Required follow-ups sent to the frontend owner:

1. The editor uses light hardcoded text on a transparent surface; keep an explicit dark code surface in light/system mode or make all editor colors theme-aware.
2. Add a visible editor focus boundary and instructions for escaping Tab indentation.
3. Replace the unconditional network-error claim that a browser draft is safe: local storage may be unavailable. Say that SQL remains in the editor, and let the persistence indicator report actual storage status.

## Evidence boundary

This review establishes acceptance guidance and inspects available source. No user research, browser screenshot comparison, contrast measurement, keyboard walkthrough or responsive rendering has yet been performed by this reviewer. Build and browser acceptance evidence belongs in the final validation report. Visual resemblance alone does not establish accessibility or execution correctness.
