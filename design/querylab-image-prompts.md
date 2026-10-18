# QueryLab generated concept prompts

Generated with the built-in image_gen tool on 17 October 2026. These are the final prompts used for the three independent concepts.

## Concept 1

Use case: ui-mockup. Generate one high-fidelity polished desktop website screenshot concept for QueryLab, landscape 16:10, ideally 1920x1200 or larger, flat front-on full viewport, no device mockup or perspective. Concept 1: MIDNIGHT WORKBENCH. Make a carefully typeset professional charcoal SQL IDE with mint accents, useful readable information density and excellent visual hierarchy. It is a real learning workspace, not a marketing landing page. Top bar: geometric Q mark and "QueryLab", links "Challenges" / "Workspace", status "MySQL · Anonymous session". Three panes: left 300px challenge brief; central dominant SQL editor over results; right 240px compact schema explorer. Left: eyebrow "OS-Q01 / Online store / Query", title "Recover inactive high-value customers", short text "Find customers worth re-engaging, after refunds." Requirements: "Net spending ≥ 500.00"; "No completed orders in the last 90 days"; "Cutoff: 1 Jul 2026 UTC"; note "A fully refunded recent order still counts as activity." Optional outlined "Reveal hint 1 of 3", separate understated "View explained solution". Editor tab "query.sql", toolbar outlined "Run", solid mint "Submit", subdued "Reset workspace". Helper "Run on practice data · Submit on fresh tests". SQL editor line numbers and syntax-highlighted readable code exactly:
-- Explore completed-order activity
SELECT
  o.customer_id,
  MAX(o.completed_at) AS last_completed_order_at
FROM orders AS o
WHERE o.status = 'COMPLETED'
  AND o.completed_at < '2026-07-01'
GROUP BY o.customer_id
ORDER BY o.customer_id;
Editor footer "Draft saved in this browser". Below editor tabs "Practice results" active and "Submission feedback"; caption "3 rows · not graded"; simple two-column result table customer_id | last_completed_order_at with 101 | 2026-03-18 10:20:00; 102 | 2026-02-09 14:30:00; 103 | 2026-05-12 09:15:00. These are outputs of exploratory starter SQL, not solved challenge. Right schema tree tables customers, orders, order_items, refunds with relevant keys/columns, restrained key icons. Palette canvas #111719 panels #192224 borders #344548 main text #EDF4F2 muted #BAC8C4 mint #8AE6BD, pale lavender/aqua code tokens. Modern sans typography, JetBrains Mono-like code, 16px body intent, crisp borders, measured spacing, 8px corners, no heavy glow. Strong professional character, pixel-sharp text, no decorative art. No avatar, sign in, accounts, progress stats, charts, streaks, leaderboards, pass badges, giant hero, invented backend settings or operating-cost details. Screenshot only; no giant concept title outside UI.

## Concept 2

Use case: ui-mockup. One high-fidelity polished desktop website screenshot concept for QueryLab. Landscape 16:10, ideally 1920x1200 or larger, flat front-on full viewport, no device frame, no perspective. Pixel-sharp readable text and carefully designed spacing; shippable-looking interface. Header small geometric Q mark and "QueryLab", "Challenges", "Workspace", "MySQL · Anonymous session". Same task: "Online store / Query / OS-Q01", headline "Recover inactive high-value customers", summary "Find customers worth re-engaging, after refunds." Rules "Net spending ≥ 500.00"; "No completed orders in the last 90 days"; "Cutoff: 1 Jul 2026 UTC"; note "A fully refunded recent order still counts as activity." Optional "Reveal hint 1 of 3" and separate "View explained solution". SQL editor tab "query.sql", line numbers, syntax-highlighted code exactly:
-- Explore completed-order activity
SELECT
  o.customer_id,
  MAX(o.completed_at) AS last_completed_order_at
FROM orders AS o
WHERE o.status = 'COMPLETED'
  AND o.completed_at < '2026-07-01'
GROUP BY o.customer_id
ORDER BY o.customer_id;
Actions outlined "Run", solid accent "Submit", subdued "Reset workspace", helper "Run on practice data · Submit on fresh tests"; draft status "Draft saved in this browser". Results tabs "Practice results" active / "Submission feedback"; "3 rows · not graded". Results columns customer_id | last_completed_order_at, rows 101 | 2026-03-18 10:20:00; 102 | 2026-02-09 14:30:00; 103 | 2026-05-12 09:15:00. This is exploratory SQL and its practice results, NOT a complete solution or passing submission. No accounts, sign-in, avatars, XP, stats, streaks, leaderboard, badges, charts, mascots, generic SaaS hero, glowing decorations, backend admin controls or giant concept title outside UI.
CONCEPT 2: FIELD NOTES. A warm editorial working studio, markedly different from a dense IDE. Ivory #F6F3EA canvas, white #FFFEFA panels, navy #202E35 text, muted #56656A, restrained rust #A54224 primary buttons with white text. Serif only for the challenge headline, humanist sans for UI, readable monospace editor. Two substantial columns: left 40% airy business brief page, right 60% tall working card. Left headline large but compact, under it "Business rules" with three numbered rules, contextual refund note, hint accordion and separate solution link. Bottom left compact visible "Tables at a glance" relational outline customers → orders → order_items → refunds with relevant join keys. Keep these relationships visible, not hidden behind a tab. Right working card has editor tabs query.sql / Schema, a dark blue #172830 SQL editor with the given code, then a light action bar, then the results grid. Ample whitespace, precise light rules, modest 10px corners, no needless nested cards. This is an actual task workspace, not a marketing page. Emphasize business comprehension next to code.

## Concept 3

Use case: ui-mockup. One high-fidelity polished desktop website screenshot concept for QueryLab. Landscape 16:10, ideally 1920x1200 or larger, flat front-on full viewport, no device frame, no perspective. Pixel-sharp readable text and carefully designed spacing; shippable-looking interface. Header small geometric Q mark and "QueryLab", "Challenges", "Workspace", "MySQL · Anonymous session". Same task: "Online store / Query / OS-Q01", headline "Recover inactive high-value customers", summary "Find customers worth re-engaging, after refunds." Rules "Net spending ≥ 500.00"; "No completed orders in the last 90 days"; "Cutoff: 1 Jul 2026 UTC"; note "A fully refunded recent order still counts as activity." Optional "Reveal hint 1 of 3" and separate "View explained solution". SQL editor tab "query.sql", line numbers, syntax-highlighted code exactly:
-- Explore completed-order activity
SELECT
  o.customer_id,
  MAX(o.completed_at) AS last_completed_order_at
FROM orders AS o
WHERE o.status = 'COMPLETED'
  AND o.completed_at < '2026-07-01'
GROUP BY o.customer_id
ORDER BY o.customer_id;
Actions outlined "Run", solid accent "Submit", subdued "Reset workspace", helper "Run on practice data · Submit on fresh tests"; draft status "Draft saved in this browser". Results tabs "Practice results" active / "Submission feedback"; "3 rows · not graded". Results columns customer_id | last_completed_order_at, rows 101 | 2026-03-18 10:20:00; 102 | 2026-02-09 14:30:00; 103 | 2026-05-12 09:15:00. This is exploratory SQL and its practice results, NOT a complete solution or passing submission. No accounts, sign-in, avatars, XP, stats, streaks, leaderboard, badges, charts, mascots, generic SaaS hero, glowing decorations, backend admin controls or giant concept title outside UI.
CONCEPT 3: DATA ATLAS. Crisp modern technical data-lab, pale cool #F2F7F6 canvas, white surfaces, ink #16313B text, muted #51636B, dark teal #00695C primary Submit, cobalt #2556B8 selection and relationships. Clean geometric sans and clear monospace SQL. Full-width top nav, below it a shallow task header containing compact title, brief summary, three visible concise rules and refund activity note; "Requirements · 4" control. Main layout left 42% schema relationship canvas, right 58% editor above results. Left heading "Explore the schema"; four compact technical entity cards on a faint dot-grid with orthogonal connectors and PK/FK tags. customers(customer_id PK, customer_name); orders(order_id PK, customer_id FK, status, completed_at); order_items(order_item_id PK, order_id FK, quantity, unit_price); refunds(refund_id PK, order_item_id FK, amount, status, refunded_at). Relationships only customers one-to-many orders, orders one-to-many order_items, order_items one-to-many refunds. Lay out cards in an elegant staggered vertical chain, logical legible clean connectors; selected orders card thin cobalt border. Right editor is white with very pale code surface, code teal/navy/plum, toolbar and results as above. Quiet support strip beneath schema with hint and separate solution link. Four-pixel corners, thin navy-grey dividers, restrained precision. Schema is a first-class reasoning tool; NOT an analytics graphic. Keep all task rules, editor and three-row results readable.

