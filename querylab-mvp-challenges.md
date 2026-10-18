# QueryLab MVP challenge outlines

Implementation update, 18 October 2026: all twelve challenges are executable. The requirements shown in the workbench and authored backend content are the final contracts; [curriculum validation](docs/curriculum-validation.md) records verification. The original planning outline below is retained as design history.

Draft for curriculum review, 17 October 2026. The two datasets and six-query/three-function/three-procedure split are confirmed. Individual challenges, business rules and routine signatures below are proposed. These outlines are not executable challenge specifications or validated fixtures.

Audience: intermediate SQL learners familiar with filtering, joins, grouping, subqueries and NULL handling. CTEs, window functions, functions, procedures and transactions are development areas. All challenges are available without prerequisite completion tracking; prerequisite notes recommend a learning order.

## Library overview

| ID | Dataset | Type | Challenge | Difficulty |
| --- | --- | --- | --- | --- |
| OS-Q01 | Online store | Query | Recover inactive high-value customers | Intermediate |
| OS-Q02 | Online store | Query | Build a monthly net-sales trend | Intermediate–advanced |
| OS-Q03 | Online store | Query | Find the leading products in each category | Intermediate–advanced |
| BI-Q01 | Business/inventory | Query | Build an actionable replenishment list | Intermediate |
| BI-Q02 | Business/inventory | Query | Compare supplier delivery reliability | Intermediate–advanced |
| BI-Q03 | Business/inventory | Query | Reconcile the stock movement ledger | Advanced |
| OS-F01 | Online store | Function | Apply consistent loyalty tiers | Intermediate; new to routines |
| OS-F02 | Online store | Function | Calculate customer net spending at a cutoff | Intermediate–advanced |
| BI-F01 | Business/inventory | Function | Calculate pack-sized replenishment quantities | Intermediate; new to routines |
| OS-P01 | Online store | Procedure | Record a refund without exceeding payment | Advanced; guided transactions |
| BI-P01 | Business/inventory | Procedure | Transfer stock atomically | Advanced; guided transactions |
| BI-P02 | Business/inventory | Procedure | Receive a delivery exactly once | Advanced; investigation |

This gives six challenges per dataset. Difficulty describes reasoning and prerequisites, not a mandatory syntax choice. Queries accept alternative correct approaches; the outlines do not require CTEs or window functions merely because hints suggest them.

## Shared dataset and grading conventions

- Use compact, deterministic synthetic fixtures with documented keys and business meanings. Hidden fixtures vary values and relationships, not the published rules.
- Default reporting cutoff: `2026-07-01 00:00:00` UTC, exclusive. Records exactly at the cutoff do not qualify. Challenges provide literal cutoffs or routine parameters; never depend on the current clock.
- Currency uses exact decimal amounts in one currency; quantities are whole units. No currency conversion, tax, shipping or fractional-stock arithmetic in MVP.
- Query results use the documented column aliases and order. Preserve duplicates where required; names are display values, never identifiers.
- Routine submissions define the specified routine; the grader invokes it on independent fixtures. Invalid business inputs use documented application errors; unexpected database errors propagate after rollback. Exact SQLSTATE/message contracts will be supplied in full specifications.
- Each challenge has three optional hints: conceptual nudge, named function/technique, partial example. Explained solutions are available separately and should discuss edge cases and another valid approach where useful.
- Failure feedback can describe a category such as incorrect tie handling or incomplete rollback without revealing hidden rows.

### Online-store entities

`customers`; `categories`; `products`; `orders`; `order_items`; `payments`; `refunds`; and a small `calendar_months` table for complete reporting periods.

Orders have a status and completion timestamp. Item rows retain the sale-time unit price and category identifier so later catalog changes cannot rewrite sales history. For analysis, eligible sales are completed orders before the cutoff. Successful payments and posted refunds have amounts and timestamps; pending/failed records do not qualify.

Refunds reference an order item and payment belonging to the same order. Every refund is an amount adjustment, not a returned-unit count. Only successful payments captured no later than the refund timestamp can fund a refund. Fixtures enforce valid cumulative refund limits. Monetary net-sales reporting and refund execution use the same underlying rules, with temporal eligibility stated per challenge.

### Business/inventory entities

`stores`; `products` (including pack size); `suppliers`; `stock` (product/store on-hand, reserved, reorder point and target); `purchase_orders`; `purchase_order_lines`; `deliveries`; `delivery_lines`; `stock_movements`; and `transfers`.

Each product has one primary supplier for MVP. A purchase order has one destination store. Deliveries are scheduled batches against that order, with fixed line quantities, a promised timestamp, a received timestamp and a status. Partial fulfillment uses multiple deliveries rather than partly receiving one delivery. Purchase-order lines hold ordered and cancelled quantities; open inbound equals ordered minus cancelled minus received quantities, floored at zero.

The stock ledger contains an opening-balance entry per stocked product/store plus signed receipts, transfers and adjustments. Seeded `stock.on_hand` is the balance at the reporting cutoff. Procedures use the same signed-movement model. Some reconciliation fixtures deliberately contain an inconsistent stock snapshot to diagnose.

## Query challenges

### OS-Q01 — Recover inactive high-value customers

**Scenario:** Marketing wants a defensible list of valuable customers who have stopped ordering, without targeting people whose purchases were mostly refunded.

**Learning goal / prerequisites:** Aggregate at the correct grain, separate lifetime value from recent activity, and apply precise date boundaries. Uses existing joins/aggregation/subquery knowledge.

**Expected behavior:**

- Compute lifetime item sales minus posted item refunds for completed orders before the reporting cutoff. Include only refunds posted before that cutoff.
- Select customers with net lifetime spending of at least 500.00 and no completed order in `[cutoff minus 90 days, cutoff)`.
- Activity is based on a completed order even if it was fully refunded. Exclude customers with no qualifying orders.
- Return `customer_id`, `customer_name`, `net_spending`, `last_completed_order_at`; order by net spending descending, then customer ID ascending.

**Grading cases:** Multiple items/payments/refunds that multiply rows in an incorrect join; exactly 500.00; an order on each time boundary; cancelled orders; fully refunded recent orders; duplicate names; no orders.

**Hints:** Separate spending from activity → consider pre-aggregation and `NOT EXISTS` → show a partial per-order refund aggregation without the final selection.

**Solution explanation:** Explain why summing a wide join inflates revenue and why a recent fully refunded order still counts as activity.

### OS-Q02 — Build a monthly net-sales trend

**Scenario:** Finance needs a six-month sales trend that includes quiet months and does not produce misleading percentage growth from a zero baseline.

**Learning goal / prerequisites:** Build a complete date series, aggregate before joining and compare adjacent periods. Introduces window functions after OS-Q01-level aggregation.

**Expected behavior:**

- Report January through June 2026 using `calendar_months`, including months with zero sales.
- Attribute completed-order gross sales and eligible refunds to the order's completion month. Refunds posted before the July cutoff reduce that original month; this is an order-cohort net-sales report, not a cash-flow report.
- Return `month_start`, `net_sales`, `running_net_sales`, `month_over_month_pct`, ordered by month ascending.
- Growth is `(current - previous) / previous * 100`, rounded to two decimals. Return NULL for January and whenever the previous month's net sales are zero. Missing sales are zero.

**Grading cases:** Empty months, refund posted after the sale month, refund at/after cutoff, multiple refunds per item, zero-to-positive transitions and decimal rounding.

**Hints:** First create one row per month → consider `LAG()` and a windowed `SUM()` → show a partial previous-month expression over an already aggregated monthly result.

**Solution explanation:** Explain the reporting attribution policy, zero-filled months and why window calculations must follow aggregation.

### OS-Q03 — Find the leading products in each category

**Scenario:** Merchandising wants the top two revenue ranks in each category, keeping tied products rather than choosing arbitrary winners.

**Learning goal / prerequisites:** Partitioned ranking and tie semantics. Uses aggregation and introduces `DENSE_RANK()`.

**Expected behavior:**

- Use completed orders in April–June 2026, subtracting posted refunds before the July cutoff for their item rows.
- Aggregate by sale-time category and product. Include only products with strictly positive net sales in the period.
- Return every product in dense revenue ranks 1 and 2 within its category. A tie at rank 2 can produce more than two products.
- Return `category_id`, `product_id`, `product_name`, `net_sales`, `revenue_rank`; order by category ID, rank, then product ID. Product ID breaks display ties only, not revenue ties.

**Grading cases:** Ties at both ranks, categories with one qualifying product, unsold/fully refunded products, duplicate product names and refunds outside the cutoff.

**Hints:** Decide whether the business wants two rows or two ranks → consider `DENSE_RANK()` → show a partial partitioned ranking over product totals.

**Solution explanation:** Contrast dense ranks with row numbers and demonstrate why adding product ID to the ranking expression destroys ties.

### BI-Q01 — Build an actionable replenishment list

**Scenario:** Buyers must reorder stock without ignoring reservations or duplicating quantities that are already on the way.

**Learning goal / prerequisites:** Combine measures from different grains and translate a business policy into arithmetic. Uses joins, grouping and conditional expressions.

**Expected behavior:**

- For every product/store, available stock is on-hand minus reserved. Inventory position is available stock plus open inbound.
- Include rows where inventory position is strictly below the reorder point. Suggested quantity reaches the target and is rounded up to a whole pack multiple.
- Use `max(target - inventory_position, 0)` before pack rounding; negative available stock remains meaningful and must not be silently clamped.
- Return `store_id`, `product_id`, `available_qty`, `inbound_qty`, `inventory_position`, `suggested_order_qty`; order by store ID, product ID. Compute inline; BI-F01 is not required.

**Grading cases:** Several deliveries per purchase-order line, partly received orders, cancelled quantities, no inbound orders, exact reorder boundary, negative availability and targets not divisible by pack size.

**Hints:** Count incoming units once, not once per delivery join → consider pre-aggregation, `COALESCE()` and `CEIL()` → show partial pack rounding without the complete report.

**Solution explanation:** Explain the difference between available stock and inventory position and show why including already received units over-orders.

### BI-Q02 — Compare supplier delivery reliability

**Scenario:** Procurement wants to compare suppliers fairly, including deliveries that were due but still have not arrived.

**Learning goal / prerequisites:** Conditional aggregation, denominator selection and cutoff-aware reporting.

**Expected behavior:**

- Include non-cancelled deliveries promised in April–June 2026. Assess their state immediately before the July cutoff, using received timestamps rather than a later current status.
- A delivery is on time when received no later than its promised timestamp and before the cutoff. Every included batch has equal weight regardless of line count or quantity.
- Report all suppliers, including those with no deliveries due: `supplier_id`, `supplier_name`, `deliveries_due`, `on_time_deliveries`, `late_or_unreceived`, `on_time_pct`.
- Return NULL percentage for no deliveries due, otherwise round to two decimals. Sort percentage descending, NULL last, then supplier ID.

**Grading cases:** Multi-line batches, exact promised timestamp, unreceived deliveries, receipt after reporting cutoff, cancelled deliveries and suppliers without eligible batches.

**Hints:** Define the denominator before calculating the percentage → consider conditional aggregation and `NULLIF()` → show a partial batch-level classification expression.

**Solution explanation:** Explain why excluding unreceived deliveries inflates reliability and why joining delivery lines must not change the batch count.

### BI-Q03 — Reconcile the stock movement ledger

**Scenario:** Operations suspects that a stock snapshot is wrong and needs to know which products went negative during the month, not just where they ended.

**Learning goal / prerequisites:** Ordered running balances and comparison of event-derived state with a stored snapshot. Introduces explicit window frames and stable event ordering.

**Expected behavior:**

- For every stocked product/store, derive the opening balance from movements before 1 June and process June movements before the July cutoff in `(occurred_at, movement_id)` order.
- Include the opening balance when finding the month's minimum balance, including when no June movements exist.
- Return only rows where the derived closing balance differs from `stock.on_hand` or the minimum balance is negative.
- Return `store_id`, `product_id`, `ledger_closing_qty`, `snapshot_qty`, `difference_qty`, `minimum_balance`; difference is snapshot minus ledger closing. Order by store ID, product ID.

**Grading cases:** Same-timestamp movements, negative intermediate balance followed by recovery, mismatched closing snapshot, no June movements, negative opening balance and events exactly at cutoff.

**Hints:** Closing balance cannot reveal an earlier shortage → consider a windowed `SUM()` with an explicit row frame → show a partial running-balance calculation with a deterministic event order.

**Solution explanation:** Explain why tied timestamps need movement IDs and why a final aggregate alone cannot detect temporary negative stock.

## Function challenges

### OS-F01 — Apply consistent loyalty tiers

**Scenario:** Different reports classify customers differently. Create a reusable function that applies one documented spending policy.

**Learning goal / prerequisites:** Routine signatures, return types and boundary-driven validation. No prior stored-function experience assumed; provide the declaration scaffold.

**Proposed signature:** `loyalty_tier(p_net_spend DECIMAL(12,2)) RETURNS VARCHAR(10)`.

**Expected behavior:** Return `STANDARD` for `[0,500)`, `SILVER` for `[500,2000)`, `GOLD` for `[2000,5000)`, and `PLATINUM` for 5000 or more. NULL input returns NULL; negative input raises the documented `INVALID_SPEND` error. Do not read or mutate tables.

**Grading cases:** Exact thresholds, one cent below/above, zero, NULL and negative input. Check return contract and absence of side effects.

**Hints:** Write the boundaries before the branches → consider `CASE` and input validation → show one incomplete branch in the routine scaffold.

**Solution explanation:** Explain branch ordering and the distinction between unknown spending and invalid spending. This is a compact introduction to routines, not a basic retrieval exercise.

### OS-F02 — Calculate customer net spending at a cutoff

**Scenario:** Reports need the same historical customer-value calculation without copying subtly different refund logic into every query.

**Learning goal / prerequisites:** Encapsulate a table-reading aggregation with precise missing-data behavior. Recommended after OS-Q01 and OS-F01.

**Proposed signature:** `customer_net_spend(p_customer_id BIGINT, p_cutoff DATETIME) RETURNS DECIMAL(12,2)`.

**Expected behavior:** Return completed-order item sales minus posted item refunds, with both order completion and refund timestamps strictly before the supplied cutoff. Existing customer with no eligible sales returns 0.00. NULL inputs raise `INVALID_ARGUMENT`; unknown customer raises `CUSTOMER_NOT_FOUND`. Do not mutate data. Spend cannot become negative in valid fixtures.

**Grading cases:** Unknown versus inactive customer, duplicate names, multiple payments/refunds, pending records, cutoff boundaries and repeat calls with different cutoffs on the same data.

**Hints:** Existence and spending are separate questions → consider separate aggregates and `COALESCE()` → show a partial customer-existence guard.

**Solution explanation:** Explain zero versus unknown customer, why the function depends on table state, and how its logic aligns with OS-Q01 without requiring that earlier solution.

### BI-F01 — Calculate pack-sized replenishment quantities

**Scenario:** A purchasing integration needs a reliable reorder calculation that respects reservations, incoming units and supplier pack sizes.

**Learning goal / prerequisites:** Translate replenishment rules into a pure, boundary-tested function. BI-Q01 is useful context but not required.

**Proposed signature:** `reorder_quantity(p_on_hand INT, p_reserved INT, p_inbound INT, p_reorder_point INT, p_target INT, p_pack_size INT) RETURNS BIGINT`.

**Expected behavior:** Inventory position is `on_hand - reserved + inbound`. Return zero when position is at least the reorder point; otherwise return the non-negative target shortfall rounded up to a pack multiple. Reject NULL inputs, negative inputs except no derived-position restriction, non-positive pack size, and target below reorder point with `INVALID_ARGUMENT`. Reserved may exceed on-hand, making position negative. Intermediate arithmetic must accommodate the documented input domain without overflow.

**Grading cases:** Exact reorder point, zero pack remainder, one-unit shortfall, negative position from reservations, zero inbound, target equal to reorder point and each invalid-input category. No table reads or mutations.

**Hints:** Triggering a reorder and sizing it are different steps → consider `CEIL()` → show partial shortfall-to-pack arithmetic.

**Solution explanation:** Explain why rounding down leaves the target unmet and why negative inventory position can be valid even when input quantities are non-negative.

## Procedure challenges

Procedure success returns exactly one documented result row; validation errors return no success row and leave business data unchanged. No dynamic SQL or elevated routine privileges are needed. Call each procedure as a top-level operation in the practice/grading runner; nested caller transactions are outside these MVP contracts. Exact signatures, error codes and result types will be finalized in executable specifications.

### OS-P01 — Record a refund without exceeding payment

**Scenario:** Customer service needs to refund part of an item safely. Retrying the same request must not create a second refund.

**Learning goal / prerequisites:** Transactional validation, cumulative limits and idempotency. Introduces transactions with guided starter structure.

**Proposed signature:** `issue_refund(p_request_key VARCHAR(64), p_order_item_id BIGINT, p_payment_id BIGINT, p_amount DECIMAL(12,2), p_refunded_at DATETIME)`.

**Expected behavior:**

- Require non-empty request key, non-NULL arguments and strictly positive amount. Item and successful payment must belong to the same completed order; refund time must be no earlier than order completion or payment capture.
- Enforce both remaining item value and remaining payment value, counting every already posted refund. Pending/failed refunds do not consume either limit.
- Update the payment's `refunded_amount` summary to the new total of posted refunds, then insert one posted refund, in the same transaction. This maintained summary makes the operation genuinely involve multiple writes and lets an injected insert failure verify rollback of the earlier update. Same key and same payload returns the original result without another update or insert; same key with different payload raises `REQUEST_CONFLICT`.
- Return `refund_id`, `refunded_amount`, `item_remaining_refundable`, reflecting the result at the original successful operation on retry. Invalid input, missing records, invalid order/payment and exceeded limits use documented errors.
- On any failure, leave refunds and related business data unchanged.

**Grading cases:** Partial/exact-remaining refunds, multiple payments, item-versus-payment limit, wrong order, cancellation, bad timestamps, repeat/conflicting key and an injected database failure. Sequential retries are required; overlapping calls on the same item/payment are an execution-contract decision to resolve before implementation.

**Hints:** Validate the item and payment budgets separately → consider a transaction, row locking and an exception handler → show a partial rollback-and-rethrow handler.

**Solution explanation:** Explain cumulative limits, retry safety and transaction ownership. Persisting the original response is one valid design, not a required storage layout.

Implementation refinement: the first development milestone uses the payment summary described above; exact error contracts and the runnable starter are now authored in `backend/app/content/challenges.py`. This outline remains a curriculum overview rather than test evidence.

### BI-P01 — Transfer stock atomically

**Scenario:** A store needs to move stock to another location without moving reserved units or leaving only one side updated after failure.

**Learning goal / prerequisites:** Multi-row atomic changes, validation and ledger consistency. Recommended after BI-Q01 and an introduction to transactions.

**Proposed signature:** `transfer_stock(p_request_key VARCHAR(64), p_product_id BIGINT, p_source_store_id BIGINT, p_destination_store_id BIGINT, p_quantity INT, p_occurred_at DATETIME)`.

**Expected behavior:**

- Require non-empty request key, non-NULL arguments, positive quantity, distinct stores and existing product/store/stock records at both ends. Creating a destination stock row is outside this contract.
- Source available stock (`on_hand - reserved`) must cover quantity. Preserve reservations and change the two on-hand quantities atomically.
- Create one transfer record and two linked ledger movements: negative at source and positive at destination, with the supplied timestamp.
- Same key and payload returns the original `transfer_id`, `quantity_transferred`, `status` (`COMPLETED`) without repeating changes. Conflicting payload raises `REQUEST_CONFLICT`.
- Insufficient stock and other validation failures leave all quantities, movements and transfers unchanged. Unexpected errors roll back the complete operation.

**Grading cases:** Exact available quantity, insufficient unreserved stock, identical/missing stores, missing stock rows, invalid quantity, replay/conflict and an injected failure after the source change. Check both balances and ledger records, not just the response.

**Hints:** Treat the transfer and its audit trail as one operation → consider a transaction, locking relevant rows and rollback → show a partial input-validation guard and transaction scaffold.

**Solution explanation:** Explain why availability differs from on-hand, why two successful independent updates are insufficient, and how consistent row-lock order helps when overlapping operations are supported.

### BI-P02 — Receive a delivery exactly once

**Scenario:** A warehouse retried a receipt after a network error and inflated its inventory. Repair the supplied faulty procedure so a delivery is applied only once.

**Learning goal / prerequisites:** Diagnose a state-changing routine, model valid state transitions and ensure multi-line atomicity. Recommended after BI-P01; starter SQL deliberately contains documented classes of defects, not an unexplained puzzle.

**Proposed signature:** `receive_delivery(p_delivery_id BIGINT, p_received_at DATETIME)`.

**Expected behavior:**

- Accept an existing scheduled delivery with at least one positive-quantity line; every referenced purchase-order line and destination stock row must exist and belong to its purchase order.
- Receiving each line must not exceed remaining ordered quantity after cancellations and previous receipts from other deliveries. Reject cancelled deliveries, invalid/NULL arguments and receipt timestamps before order creation.
- Atomically increment destination stock, add one linked positive ledger movement per delivery line, and mark the delivery received at the supplied timestamp. Do not alter reservations or ordered quantities.
- For an already received delivery, the same timestamp returns the original `delivery_id`, `lines_received`, `units_received`, `status` (`RECEIVED`) without changes. A different timestamp raises `REQUEST_CONFLICT`.
- Any invalid line or database failure rolls back every line and leaves the delivery unreceived.

**Grading cases:** Multi-product receipt, already received delivery, conflicting retry, cancelled/missing delivery, over-delivery, missing stock row, invalid line quantities and a failure after processing an earlier line. Verify balances, movement counts and delivery status together.

**Hints:** A successful first line does not mean the delivery succeeded → consider state guards, a transaction and a rollback handler → show a partial already-received branch without the whole repair.

**Solution explanation:** Explain why idempotency requires persisted state, how line-level success differs from delivery-level success, and why rollback must cover audit movements too.

## Recommended first vertical slice

Use **OS-Q01, OS-F01 and OS-P01** against a small online-store fixture. This avoids adding inventory entities solely to run the first procedure while still proving a query, a function and an atomic state-changing procedure. BI-P01 follows when the inventory dataset is added. This is a proposed refinement of the brief's example stock-transfer slice.

## Before these become implementation-ready

1. Review the individual themes and proposed business rules; keep the confirmed count/type split.
2. Finalize versioned schemas, constraints, routine signatures, error precedence/contracts and query result types. Define timestamp precision and numeric rounding consistently.
3. Define whether operations on the same anonymous workspace are serialized. If concurrent routine calls are allowed, specify and test lock behavior and conflicting operations. Cross-learner isolation remains required regardless.
4. Build visible fixtures with worked outputs, hidden fixture variants, authored reference solutions and alternative-correct/known-wrong submissions. The case lists above are grading intentions, not evidence of passing tests.
5. Write all three actual hints and an explained solution for each challenge; validate them against executable fixtures. No runnable solutions are supplied by this outline document.
