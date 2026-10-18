# Focused Midnight Workbench concept

17 October 2026. User-selected simplification following the UI Designer's [review](../docs/ui-simplification-review.md). [Concept image](querylab-04-focused-workbench.png). The user authorized implementation after reviewing this mockup; implementation evidence is recorded separately in the [focused UI QA report](../docs/focused-ui-qa.md).

Default view shows a compact challenge overview and wider editor. Full Requirements and Expected output are conspicuous collapsed sections; Schema opens on request; results expand after execution; hints/solutions appear on demand. Focus hides the brief while preserving execution and recovery controls.

The SQL shown is an illustrative unfinished draft, not a solution. The brief is explicitly an overview: full unchanged business rules, boundaries and expected output must remain available before writing or submitting. The image shows the default pre-execution state; the review specifies expanded rules, schema docking, results/errors and narrow-screen behavior.

Generated with the built-in image_gen tool using the imagegen skill; no CLI fallback. Saved project asset: `design/querylab-04-focused-workbench.png`. Original concepts and application screenshots are preserved.

## Generation prompt

```text
Use case: ui-mockup.
Asset type: high-fidelity desktop website concept for QueryLab's proposed simpler Midnight Workbench. A clean, realistic straight-on full browser-content screenshot, landscape 1536 by 1024 composition, no device frame.
Primary request: simplify a real SQL practice workbench for intermediate learners. The challenge and SQL editor are the clear focus, supporting information is disclosed on demand. Use restrained charcoal/near-black surfaces (#101819, #151e20), very subtle borders #2b3b3d, warm off-white text, muted secondary text, mint #87e5c0 only for one main action and small accents. Excellent readable sans-serif UI type, monospaced SQL. Quiet polished developer tool with generous spacing, no gradients, glow or marketing.
Layout: slender 56px top bar, small mint geometric Q symbol and 'QueryLab.' on left, 'Challenges' simple navigation nearby. On right one small green status dot and 'Connected' text button, no duplicated environment lines.
Below top bar, 24px margins. Two-pane default only: a 320px-wide challenge panel at left and a much larger editor at right filling all remaining width and most height. No right schema column visible in default view.
Left panel: subtle 'OS-Q01  /  Online store' metadata, large title 'Recover inactive high-value customers' wrapped naturally on 3 lines. Small 'Overview' label. Exactly two concise sentences below: 'Find valuable customers who have stopped ordering. Account for refunds when calculating their spending.' Then separated collapsed disclosure rows with chevrons: 'Requirements' with a small '5 rules' badge and 'Expected output'. The Requirements row must be easy to find, not faint. These are obvious controls containing the full task specification on click. Lower down an understated lightbulb action 'Get a hint' and a text link 'More help'. No open hints, numbered paragraphs, solution SQL, wall of text or extra cards.
Right editor: one compact toolbar with left 'SQL editor' title, right outlined labeled controls 'Schema' (table icon) and 'Focus' (expand icon), then distinct outlined 'Run' play button and solid mint 'Submit' button. No separate file-tab row or explanation row. Below, a large monospaced SQL editing area with 10 readable lines, syntax highlighting and discreet line numbers. Render this illustrative unfinished draft exactly with realistic indentation:
WITH customer_activity AS (
    SELECT customer_id,
           MAX(completed_at) AS last_order_at
    FROM orders
    WHERE status = 'COMPLETED'
    GROUP BY customer_id
)
SELECT customer_id, last_order_at
FROM customer_activity;
Code is an illustrative draft, not a final challenge answer. Keep most of editor uncluttered empty writing space. Small bottom-right editor status 'Draft saved'. A compact collapsed 42px strip below editor labeled 'Results' with chevron and secondary text 'Run your query to see results'. Before execution, no blank large result table, feedback panels, grades or success callouts. No persistent global footer or motivational mottos.
Composition focus: dominant editor, short challenge summary with obvious collapsed requirements, hidden schema accessible via clear Schema button, one strong mint Submit button. Functional readable UI controls, realistic spacing, restrained borders, no ornamental cards, no annotation arrows, no explanatory captions outside the app, no login, avatar, stats, progress dashboard, search bar, fake charts, extra navigation or mobile inset. Preserve QueryLab identity and Midnight palette. This is a design mockup, not an implementation screenshot.
```

