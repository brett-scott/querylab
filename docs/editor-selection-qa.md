# Run highlighted SQL

Tab update, 18 October 2026: Tab now inserts a tab character at the caret when nothing is selected, including at the end or middle of a line. With selected text it retains block indentation; Shift+Tab retains outdent. Both frontend builds passed. The expanded browser scenario passed in 6.8 seconds, checking exact saved text, continued typing after the inserted tab, selected-line indentation/outdent, and the existing execution/selection behavior.

18 October 2026. Run and Ctrl/Command+Enter execute the exact highlighted CodeMirror text. Without a selection they execute the full draft. Submit and Ctrl/Command+Shift+Enter continue to grade the full draft. Selection does not replace the saved editor content.

The Run button reads CodeMirror's stored selection, which survives the button taking focus. The frontend sends only that SQL to the existing execution API; backend execution and grading rules are unchanged. Partial statements are sent as selected, without automatically expanding their boundaries. A whitespace-only selection does not fall back to running the full draft.

Both development and helper-mode frontend builds passed and both local previews were updated. The real-MySQL browser test in `qa/tests/editor-selection.spec.js` passed in 5.4 seconds, checking:

- A highlighted multi-statement block runs through the toolbar, excluding an unselected write and invalid SQL. Both selected results appear and the draft stays intact.
- A backward selection runs through the keyboard shortcut, with the exact selected text in the API request.
- No selection sends the full two-statement script and returns both results.
- Submit with a partial selection sends the complete reference answer and passes grading.

An initial test run used the MySQL window-function name FIRST_VALUE as an unquoted result alias and failed on that fixture SQL. The alias was corrected; the final test passed. No application change was needed for that failure.
