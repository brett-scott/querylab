# QueryLab: three visual concept directions

17 October 2026. UI Designer and UX Researcher collaboration. These are visual explorations for choosing a design direction, not implemented interfaces or validated usability/accessibility evidence.

Sources: [MVP decisions](../querylab-mvp-decisions.md), [challenge outlines](../querylab-mvp-challenges.md), and [UX concept notes](querylab-ux-concept-notes.md).

Selection: **Concept 1 — Midnight Workbench**, confirmed by the user on 17 October 2026. Its [generated image](querylab-01-midnight-workbench.png) is the MVP visual reference. The remaining concepts are retained as exploration history. Selection establishes visual direction; interactive states and final schema details still require implementation design and validation.

## Shared comparison contract

All three images depict the same desktop challenge and the same exploratory SQL state. Layout and visual hierarchy change; scope and content do not. This lets the review focus on the experience rather than differing features.

- Product: QueryLab, an anonymous hosted practice workspace for intermediate SQL learners.
- Challenge: **OS-Q01 — Recover inactive high-value customers**. Dataset: **Online store**. Type: **Query**.
- Scenario: **Find customers worth re-engaging, after refunds.**
- Visible rules: **Net spending ≥500.00**; **No completed orders in the last 90 days**; **Cutoff: 1 Jul 2026 UTC**.
- Important rule note: **A fully refunded recent order still counts as activity.**
- Full brief must also define completed-order lifetime item sales less posted refunds before cutoff, the inclusive inactivity start/exclusive cutoff, and the four output columns ordered by net spending descending then customer ID ascending. The image need not display this entire specification; implementation must make it available through the brief or Requirements control.
- Persistent controls: **Run**, **Submit**, **Reset workspace**. Explain **Run on practice data · Submit on fresh tests**. Reset retains the editor draft.
- Guidance: **Reveal hint 1 of 3**, plus separately **View explained solution**. Start with hints unrevealed; guidance remains optional.
- Persistence: **Draft saved in this browser**. Avoid wording that implies an account, cross-device resume or saved database changes.
- Navigation: **Challenges / Workspace**. Environment label: **MySQL · Anonymous session**.
- Results tabs: **Practice results / Submission feedback**. Visible result status: **3 rows · not graded**. In implementation the idle feedback pane says **Submit to check your answer**.
- Do not add sign-in, avatars, XP, completion history, leaderboards, streaks, a progress dashboard, decorative charting, a mascot or a marketing hero.

The starter SQL deliberately explores completed-order activity; it is not a finished answer. A recent May order appears in the practice output so the image does not silently imply that the draft already satisfies the inactivity rule.

```sql
-- Explore completed-order activity
SELECT
  o.customer_id,
  MAX(o.completed_at) AS last_completed_order_at
FROM orders AS o
WHERE o.status = 'COMPLETED'
  AND o.completed_at < '2026-07-01'
GROUP BY o.customer_id
ORDER BY o.customer_id;
```

Illustrative practice rows, matching this exploratory query rather than the final challenge output:

| customer_id | last_completed_order_at |
| --- | --- |
| 101 | 2026-03-18 10:20:00 |
| 102 | 2026-02-09 14:30:00 |
| 103 | 2026-05-12 09:15:00 |

Example schema is illustrative until the executable specification is written: customers → orders → order_items → refunds. Show only these relationships; payments must not be joined into spending totals merely for visual completeness.

## 1. Midnight Workbench

**Design intent:** A professional IDE with the task, editor and schema always available for frequent cross-referencing. It should feel like a purpose-built SQL working environment rather than a generic code editor reskin.

**Composition:** Full-viewport charcoal application. A slim 56px top bar, then three resizable pane concepts: roughly 300px task/requirements left, flexible SQL editor and practice-result grid center, 240px schema outline right. Run and Submit sit together in the editor toolbar; Reset workspace is a subdued utility. Left pane ends with the optional hint and solution actions. Center editor takes approximately 60% of workspace height, results 40%.

**Foundation:** Canvas `#111719`; panels `#192224`; borders `#344548`; primary text `#EDF4F2`; secondary text `#BAC8C4`; mint action accent `#8AE6BD` with dark text. Syntax uses restrained aqua/lavender. Clean sans UI, JetBrains Mono-style code. An 8px corner radius, thin separators, no neon glow. Body text aims at 16px; rendered images may not preserve exact sizes.

**Components:** Compact challenge metadata, plain requirements list, optional hint disclosure, query.sql tab, bordered Run, filled mint Submit, unobtrusive reset action, schema tree with keys, result/feedback tabs and a low-key browser draft status.

**UX hypothesis:** Best for learners who repeatedly compare business rules, joins and their current SQL.

**Tradeoff and mitigation:** Three columns can feel dense. Keep schema shallow by default, avoid stacked toolbars, preserve useful code width and make panes collapsible/resizable in implementation. On narrower screens, move schema behind a tab before shrinking the editor to an unusable width.

**Image prompt:** Render one polished front-on 16:10 desktop QueryLab website screenshot, no device frame. Professional dark SQL IDE with charcoal panels and restrained mint accent. Use the shared challenge, nine-line exploratory SQL and three-row practice result exactly as specified above. Three-pane workspace: challenge and business rules left; large editor with Run / Submit / Reset workspace and result grid center; compact customers/orders/order_items/refunds schema outline right. Keep challenge title, cutoff, three core rules and fully-refunded-order note readable. Show Reveal hint 1 of 3, View explained solution, Draft saved in this browser, Run on practice data · Submit on fresh tests, and 3 rows · not graded. Precise 8px corners, thin dividers, sans UI and clear monospace code. No login, avatar, dashboard statistics, streaks, mascot, huge hero, decorative chart or passing state.

## 2. Field Notes

**Design intent:** An inviting, serious learning studio that foregrounds the business scenario without turning intermediate practice into a basic lesson.

**Composition:** Ivory page with two substantial columns. Left 40% is a spacious business brief: metadata, expressive challenge heading, scenario, numbered business rules, optional hint and explained-solution actions. A compact Tables at a glance section keeps the schema relationships in view. Right 60% is one tall working card with a dark blue editor, light action row and light results. This is a working exercise screen, not a landing page.

**Foundation:** Canvas `#F6F3EA`; panels `#FFFEFA`; text `#202E35`; secondary `#56656A`; restrained rust primary `#A54224` with white text; code surface `#172830`. Serif appears only in the challenge headline, with humanist sans interface text and monospace code. Gentle 10px corners and subtle rules; ample spacing without oversized cards or shadows.

**Components:** Scenario header, numbered requirements, hint accordion, separate explained-solution link, four-table schema summary including join keys, SQL/Schema tabs, dark editor, outlined Run, rust Submit, utility Reset workspace, result/feedback tabs and draft status.

**UX hypothesis:** Best for understanding the scenario and exception rules before writing SQL.

**Tradeoff and mitigation:** An editorial brief can reduce available code space, while a tab-only schema slows joins. Keep the compact schema summary persistently visible, provide a larger Schema tab, and allow the brief to collapse after reading. Do not require scrolling through a long lesson to reach the editor.

**Image prompt:** Render one polished front-on 16:10 desktop QueryLab website screenshot, no device frame. Warm ivory editorial SQL working studio, restrained rust actions, dark blue code editor. Use the shared challenge, exploratory SQL and matching three-row practice result. Two generous columns: left 40% business brief with a serif challenge title, scenario, numbered requirements, the fully-refunded-order note, optional hint and separate solution actions; right 60% working card with dark editor above light actions and results. Include Tables at a glance with customers → orders → order_items → refunds and join keys at the bottom of the brief so schema is visible. Run outlined, Submit solid rust, Reset workspace subdued. Show Draft saved in this browser, Run on practice data · Submit on fresh tests, Practice results / Submission feedback, and 3 rows · not graded. Clear sans body text, readable monospace code, fine rules, modest 10px corners. No signup, avatar, user statistics, hero, mascot, charts or fictional success feedback.

## 3. Data Atlas

**Design intent:** A crisp data-lab workspace where relationships are a first-class tool for thinking about aggregation grain and avoiding duplicated totals.

**Composition:** A full-width shallow challenge strip below navigation shows the title, scenario, three rule chips, important exception note and a persistent Requirements · 4 control. Main workspace splits into a relationship canvas left 42% and editor/results right 58%. The canvas shows four connected technical table blocks with key fields. Below the workspace a quiet support strip exposes optional hints and the explained solution.

**Foundation:** Canvas `#F2F7F6`; surfaces white; text `#16313B`; secondary `#51636B`; primary teal `#00695C` with white text; cobalt relationship/selection accent `#2556B8`. Crisp sans typography and monospace code, 4px corners, fine navy-grey dividers and a very pale code surface. No decorative analytics.

**Schema blocks:** customers(customer_id PK, customer_name); orders(order_id PK, customer_id FK, status, completed_at); order_items(order_item_id PK, order_id FK, quantity, unit_price); refunds(refund_id PK, order_item_id FK, amount, status, refunded_at). Orthogonal one-to-many connectors only: customers → orders → order_items → refunds. A thin cobalt border identifies the selected orders table.

**Components:** Compact task strip, requirement chips with a full brief control, entity cards, selected relationship state, light SQL editor, Run/Submit/Reset actions, practice-result table, feedback tab and support strip.

**UX hypothesis:** Best for reasoning about joins, one-to-many relationships and where to aggregate.

**Tradeoff and mitigation:** A large schema can steal editor space and a collapsed brief can hide crucial rules. Keep the three headline rules plus the exception visible, retain a clear Requirements control, and allow schema collapse. On smaller screens schema becomes a dedicated tab instead of compressing both panels.

**Image prompt:** Render one polished front-on 16:10 desktop QueryLab website screenshot, no device frame. Crisp modern schema-centric data lab on a pale cool canvas, navy ink, white surfaces, deep teal Submit and cobalt relationship lines. Use the shared challenge, exploratory SQL and matching three-row practice result. A shallow full-width task strip shows the title, scenario, three concise rule chips, fully-refunded-order note and Requirements · 4 control. Main workspace: left 42% Explore the schema canvas with the four exact technical entity blocks and correct one-to-many relationships; right 58% light SQL editor above result grid. Selected orders card outlined cobalt. Run outlined, Submit deep teal, Reset workspace subdued; readable execution helper and Draft saved in this browser. Results show Practice results / Submission feedback and 3 rows · not graded. Quiet bottom strip has Reveal hint 1 of 3 and View explained solution. Use clean sans typography, readable mono code, precise orthogonal connectors, 4px corners and thin dividers. No hero, accounts, avatar, statistics, leaderboard, decorative charts, mascot or implied passing answer.

## Selection and implementation notes

UX Researcher review supports all three as distinct, testable directions. Midnight Workbench emphasizes frequent cross-referencing; Field Notes emphasizes reading and interpreting the task; Data Atlas emphasizes relationship reasoning. These are hypotheses, not conclusions from user testing.

Review each concept on four tasks: locate the refund exception; identify the join keys; explain what Run versus Submit does; find help without opening the solution. Favor the layout that makes these tasks clear while leaving comfortable editing space. Compare the visual direction separately from the generated bitmap's incidental text errors.

WCAG AA is the implementation target. Bitmap concepts cannot certify compliance. Verify actual text contrast, 200% text scaling, keyboard operation, visible focus, editor accessibility, error announcements, semantic table structure and reduced-motion behavior in a working prototype. Interactive targets should aim for 44px where practical. No color alone should communicate grading, errors or relationship selection.

For every direction, implementation must supply running/cancel states, capacity-busy feedback, SQL error details, expired-workspace notice, reset confirmation that explicitly preserves the draft, and visible result truncation. These states are outside the static image comparison and must not be mistaken for resolved behavior.
