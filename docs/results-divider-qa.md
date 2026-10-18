# Draggable results divider

18 October 2026. Replaced the Results height range slider with a draggable divider between the SQL editor and results. Resizing updates both panes live. The bounds follow the available workspace height while keeping at least 200 px for the editor and 148 px for results. Narrow layouts retain stacked panels.

The separator supports pointer capture, keyboard arrows, Home/End, and Escape to undo an active drag. Pointer release, cancellation, window blur and unmount clear the drag state. Collapsing and reopening results retains the selected proportion within the available bounds.

Verification used real MySQL and installed Edge through Playwright:

- Both development and helper-mode frontend builds passed and both local website previews were updated.
- The focused browser scenario passed on the final build: a 96 px drag enlarged results and reduced the editor by the same amount, including when the pointer moved outside the handle. Release stopped resizing; Escape restored the original size. SQL and the original editor DOM remained intact.
- Keyboard resizing and the short-window maximum were checked, along with collapse/reopen and responsive layouts at 1600, 1024, 800 and 375 CSS pixels.
- All five workbench browser scenarios passed, covering Run, Submit, drafts, inventory routines/reset, errors, cancellation and storage recovery.

The first combined run exposed a test timing assumption: schema refresh briefly changes the available height after Run completes. The focused test now waits for workspace readiness and the settled divider before checking End. Its final rerun passed in 6.8 seconds. No backend behavior changed.

[Inspected drag screenshot](../qa/screenshots/focused/results-drag-resized.png). The historical slider evidence in [focused UI QA](focused-ui-qa.md) is superseded for this control. Direct touch/pen gestures and screen-reader announcements were not separately tested.
