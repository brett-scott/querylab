# QueryLab concept UX notes

17 October 2026. Prepared with the UI Designer for three comparable concept images.

## Evidence and questions

Evidence comes from the confirmed [MVP decisions](../querylab-mvp-decisions.md) and proposed [challenge outlines](../querylab-mvp-challenges.md). No learner interviews or usability tests have been conducted. The recommendations below are design hypotheses, not measured user preferences or accessibility certification.

The concepts explore three questions: can intermediate learners understand the business rules while writing SQL; can they find relevant table relationships without losing their place; and can they distinguish practice execution from grading and recovery?

## Shared comparison contract

Use the same desktop exercise, OS-Q01 **Recover inactive high-value customers**, in all three images. Use the same content and task state so layout and visual treatment are the comparison variables.

- Show online-store dataset, query type and intermediate difficulty. Navigation leads back to the challenge library, without an account or statistics dashboard.
- Visible task summary: find customers with net lifetime spend of at least 500.00 and no completed order in the last 90 days, assessed before 1 July 2026 UTC. A recent fully refunded completed order still counts as activity. Detailed requirements retain cutoff boundaries and required output columns.
- Make the SQL editor the main work surface, with schema access nearby. Keep the task available while editing. Expected output columns are `customer_id`, `customer_name`, `net_spending`, `last_completed_order_at`.
- Show practice results as **Practice results — not graded**. Keep submission feedback separate. A populated result table must not imply a challenge pass.
- Label controls **Run**, **Submit**, and **Reset workspace**. Supporting copy explains Run uses practice data; Submit checks fresh test data. Reset restores practice data and keeps the editor draft.
- Show **Draft saved in this browser**. Communicate session recreation when it happens; a persistent expiry countdown is unnecessary until session behavior is specified.
- Offer **Reveal hint 1 of 3** on request and a separate **View explained solution** action. Do not reveal solutions automatically. Suggested first hint: “Separate lifetime spending from recent activity.”
- Keep schema details, errors, cancellation, grading feedback and progressive hints representable even when the concept screenshot shows a calmer state.

Displayed schemas, SQL and result rows in the concept images are illustrative. They are not validated fixtures or executable specifications.

## Three layout hypotheses

| Concept | Main arrangement | Expected benefit to test | Main risk and response |
| --- | --- | --- | --- |
| Midnight Workbench | Persistent brief at left; editor and results centrally; compact schema at right. Dark, professional workspace. | Frequent cross-reference without opening panels. | Density can overwhelm or force tiny text. Prioritize editor width, allow resizable/collapsible rails and avoid several simultaneous nested scroll regions. |
| Field Notes | Scenario and requirements at left; editor and results at right. Warm light surfaces with a distinct code surface. Schema available through a nearby tab. | Business rules stay readable while solving. | Hidden schema may slow joins. Expose relevant table names/keys and a clearly labeled Schema control near the editor. |
| Data Atlas | Relational schema at left; editor and results at right; shallow task summary above, detailed brief accessible. Pale mint and navy. | Relationship and grain reasoning stay visible. | A collapsed brief can hide crucial rules. Keep spending, inactivity and cutoff rules visible; provide an explicit Requirements control. |

The UX Researcher and UI Designer agree that these should differ in information hierarchy, not only palette. No preferred direction is claimed before comparison with learners.

## Inclusive design and validation

Generated images cannot establish contrast compliance, keyboard access or screen-reader behavior. Implementation must test text and control contrast, visible focus, keyboard navigation between panes, a way to leave the editor without a mouse, semantic result tables, readable non-color error/status labels, and announced execution/grading state changes. Resizable panes and local scrolling must remain usable with zoom and longer SQL/results. Small-screen behavior needs a dedicated design pass.

For an initial formative review, recruit 5–6 consenting intermediate SQL learners with varied coding-tool familiarity; include keyboard-only and low-vision/zoom use where possible. This sample identifies usability issues and does not support population preference percentages. Counterbalance concept order to reduce first-view bias. Use synthetic tasks and avoid collecting personal SQL or unnecessary identifying data.

Ask each learner to locate the business boundary rules, identify the refund relationship, explain Run versus Submit, request a hint without revealing the solution, and restore practice data without losing SQL. Record task success, misunderstandings, navigation friction and confidence, with consent for any recordings. Treat aesthetic preference as separate from task performance. Validate keyboard, zoom and assistive-technology behavior again on an interactive prototype because static images cannot test it.
