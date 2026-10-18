MySQL Training Lab — AI Agent Handoff Brief
Purpose and decision status
Build a practical MySQL training application where a learner solves realistic scenarios using different datasets and difficulty levels. Exercises must cover data analysis, functions and stored procedures, with room for database design, transactions, debugging and performance work.
This brief summarizes the product discussion. It is a starting specification, not evidence that implementation has begun.
- User requirements: multiple datasets; varied scenarios and difficulty; hands-on SQL, including functions and stored procedures; a usable application.
- Recommended approach: a local web app connected to a real MySQL server. A desktop executable remains an alternative or later packaging option.
- Working name: QueryLab was recommended but has not been confirmed. Other suggestions included SQL Lab, SQL Gym, QueryQuest, QueryCraft and SQL Sandbox. Name availability has not been checked.
- Proposed stack and scope: the technologies, challenge count and milestones below are recommendations, not previously approved commitments. Use them as working defaults and document material changes.
Product experience
The learner chooses a dataset, topic and difficulty, reads a business scenario, explores the schema and sample data, writes SQL, runs it, then submits it for grading. They receive actionable feedback, can request progressively stronger hints, and can reveal an explained solution.
Provide a simple workspace with a navigation sidebar, scenario/schema panel, SQL editor, results grid and feedback area. Support table inspection, keys and relationships, sample rows, MySQL error messages, multiple result sets where needed, and resetting the exercise. Keep the interface focused and uncluttered.
Save attempts, solutions, feedback, hint usage and progress independently of the practice databases. Allow learners to resume work. Distinguish independent passes from completions with assistance.
Learning content
Area	Example task
Foundations	Filter products by stock level, sort results and handle missing values.
Joins and aggregation	Calculate completed-order spending per customer without double-counting.
Advanced analysis	Use CTEs and window functions for rankings, running totals and retention.
Functions	Return a customer's net spending or determine a loyalty tier.
Stored procedures	Produce a parameterized report or process a stock transfer.
Data changes	Correct records, apply updates and remove duplicates.
Schema design	Create tables, relationships, constraints and views.
Transactions	Keep multi-step changes atomic and handle errors.
Debugging	Repair a query or routine with incorrect behaviour.
Performance	Read execution plans and improve query/index design.


Difficulty
1. Foundations: one table, explicit requirements and guided help.
2. Working SQL: joins, grouping, conditional expressions and basic business rules.
3. Advanced analysis: multi-table logic, CTEs, window functions and edge cases.
4. Database programming: routines, validation, transactions and error handling.
5. Investigation: diagnose defects, optimize execution and combine skills.
Difficulty and guidance are separate controls. An advanced exercise may still offer hints. Start with guided lessons, standalone challenges and a free-practice sandbox; add connected mini projects later.
Dataset plan
Dataset	Core entities	Scenario themes
Online store	Customers, orders, order items, products, payments, refunds	Revenue, customer behaviour, purchasing reports and refunds
Game achievement platform	Players, games, achievements, unlocks, play sessions	Completion, rarity, player activity and leaderboards
Business and inventory	Stores, suppliers, products, stock, deliveries, transfers	Low stock, supplier performance and stock movement


Potential later packs: hotel bookings and support-desk operations.
Use deterministic synthetic data with documented relationships and business meanings. Include meaningful edge cases such as customers with no orders, duplicate names, optional NULL values, cancellations, partial refunds and tied rankings. Provide fixed reporting dates so answers do not drift with the current date. Larger dataset variants can support performance work later.
Example exercises
Analysis — inactive high-value customers: Return customers who previously spent at least $500 but have no completed orders in the 90 days before a supplied reporting date. Return ID, name, qualifying lifetime spending and last completed-order date, ordered by spending descending. The exercise specification must define refund handling, time boundaries, tie-breaking and customers with no qualifying purchases.
Function — loyalty tier: Create a function with a specified name, input type and return type that maps eligible spending to a tier. Test threshold boundaries, NULL inputs and negative inputs according to an explicitly documented policy.
Procedure — stock transfer: Create a procedure with specified product, source, destination and quantity parameters. Validate inputs and stock availability, update both locations atomically, and return the documented outcome. Test successful transfers, insufficient stock, missing records, non-positive quantities, identical locations and failure partway through the operation.
Challenge specification and grading
Define a versioned challenge format containing: ID/title, dataset version, topic, difficulty, prerequisites, scenario, exact requirements, starter SQL, permitted operations, visible examples, hidden test fixtures, grading rules, hints, reference solution and explanation. Routine challenges must define exact signatures and result/error contracts.
Grade observable behaviour rather than matching SQL text. Accept different correct approaches. If an exercise explicitly requires a technique such as a window function, state that requirement and validate it separately from result correctness.
- Queries: compare required columns and values; preserve duplicate counts; require row order only when specified. Define alias, type, decimal precision, NULL, date/time and collation expectations per challenge.
- Functions: call with normal, boundary, missing and invalid inputs; verify return values and expected errors.
- Procedures: verify parameters, all required result sets/output parameters, state changes, validation and rollback behaviour.
- Schema tasks: inspect required objects, columns, keys and constraints.
- Performance tasks: prove correctness first, then evaluate plans on controlled data. Do not use a single machine-dependent timing threshold as the sole grade.
Use fresh fixtures for test cases so one attempt cannot contaminate another. Keep hidden fixtures and reference answers inaccessible to the learner's SQL account. Provide helpful failure categories without revealing hidden rows. Report infrastructure failures separately from incorrect submissions.
Hints should progress from concept to approach to partial example. Solutions should explain reasoning and valid alternatives. Start with authored, validated challenges and deterministic variations. AI-generated challenges or feedback are later enhancements; AI should not be the authority for correctness.
Recommended technical design
- Frontend: React and TypeScript with a MySQL-aware editor.
- Backend: Python/FastAPI for exercise orchestration, execution, grading and progress APIs.
- Database engine: real MySQL; MySQL 8.4 is a proposed training baseline. Pin the selected release and SQL mode for reproducibility rather than using an unversioned latest image.
- Local orchestration: Docker Compose with documented startup, database readiness checks and seed/reset commands.
- Progress storage: a separate application database or storage area that learner SQL cannot access.
- Packaging: local browser interface first; evaluate a desktop launcher/wrapper after the learning loop works.
This requires services running on the user's computer; a static HTML preview or a standalone chat UI is insufficient for full MySQL execution. A desktop wrapper still needs a database engine. Avoid substituting SQLite or simulated results for MySQL exercises.
The backend must handle routine definitions as complete statements. Do not split SQL naively on semicolons. DELIMITER is a client directive; the editor/runner must either support it deliberately or explain the supported submission format.
Execution isolation and reset requirements
Run learner SQL only against disposable practice environments, using schema-scoped permissions and no server-administration privileges. Protect progress storage, seed sources, test assets and other workspaces. Keep SQL connections on the backend; never give the browser administrative credentials.
Implement bounded results, execution deadlines, cancellation and resource limits. An HTTP timeout alone does not stop a running query or routine: cancel the database execution or recycle the disposable environment when necessary. Restrict stored routine privileges/definers so routines cannot gain administrative access.
Reset tables, data, routines and other created objects from known fixtures. Do not rely on transaction rollback to undo every exercise: MySQL DDL and routine creation can cause implicit commits. The local personal-use deployment is the initial target; public multi-user hosting needs a separate isolation review.
Proposed version one
Target three datasets and approximately 36 authored, tested challenges. Prioritize queries, functions, procedures and a small set of transaction/debugging exercises. Include schema exploration, SQL execution, automatic grading, hints, explained solutions, saved attempts and a resettable sandbox. Expand schema-design and performance content once core grading is reliable.
Defer public hosting, multiplayer features, leaderboards, desktop installers, a large challenge marketplace and unrestricted AI-generated content.
Suggested agent responsibilities
Workstream	Ownership
Architecture and integration	Repository structure, shared contracts, local setup and cross-component decisions
Dataset and curriculum	Schema, deterministic seed data, challenge definitions, hints and reference solutions
Execution and grading	MySQL runner, isolation, reset, cancellation, fixtures and comparisons
Frontend and learner experience	Challenge browser, editor, schema explorer, results, feedback and progress
Validation and integration	End-to-end exercise verification, grading edge cases and startup/reset checks


These are responsibilities for the receiving team, not a requirement for five separate agents. Agree challenge and execution API contracts before parallel implementation. Assign file ownership to reduce conflicting edits.
First milestone and acceptance criteria
Build one complete exercise of each core type against a small online-store dataset: one analysis query, one function and one procedure that changes data.
The milestone is complete when:
1. A documented local command starts the app and MySQL and waits for readiness.
2. The learner can inspect the schema, edit SQL, run it and view real results/errors.
3. Each challenge can be submitted and graded against visible and hidden fixtures.
4. The grader accepts multiple correct queries and rejects plausible incorrect solutions, including hard-coded sample answers.
5. Function boundary cases and procedure validation/rollback cases are exercised.
6. Reset removes learner-created objects and restores fixtures without losing progress.
7. A long-running submission can be stopped, and the workspace remains recoverable.
8. The learner's database credentials cannot access progress, hidden tests or reference answers.
9. Hints, explanations, attempts and progress work through the UI and survive an app restart.
After this vertical slice passes, expand to the three proposed datasets and challenge library. Prioritize accurate execution, reproducible resets and trustworthy feedback before adding breadth or visual polish.