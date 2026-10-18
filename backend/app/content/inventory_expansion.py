"""Executable inventory reporting and pure replenishment exercises."""

REPLENISHMENT = """WITH received AS (
    SELECT dl.purchase_order_line_id, SUM(dl.quantity) AS received_qty
    FROM delivery_lines dl JOIN deliveries d ON d.delivery_id=dl.delivery_id
    WHERE d.status='RECEIVED' AND d.received_at < '2026-07-01'
    GROUP BY dl.purchase_order_line_id
), inbound AS (
    SELECT po.store_id, pol.product_id,
           SUM(GREATEST(pol.ordered_qty-pol.cancelled_qty-COALESCE(r.received_qty,0),0)) AS inbound_qty
    FROM purchase_order_lines pol
    JOIN purchase_orders po ON po.purchase_order_id=pol.purchase_order_id
    LEFT JOIN received r ON r.purchase_order_line_id=pol.purchase_order_line_id
    WHERE po.created_at < '2026-07-01'
    GROUP BY po.store_id,pol.product_id
), positions AS (
    SELECT s.*,p.pack_size,s.on_hand-s.reserved AS available_qty,
           COALESCE(i.inbound_qty,0) AS inbound_qty,
           s.on_hand-s.reserved+COALESCE(i.inbound_qty,0) AS inventory_position
    FROM stock s JOIN products p ON p.product_id=s.product_id
    LEFT JOIN inbound i ON i.store_id=s.store_id AND i.product_id=s.product_id
)
SELECT store_id,product_id,available_qty,inbound_qty,inventory_position,
       ((GREATEST(target_qty-inventory_position,0)+pack_size-1) DIV pack_size)*pack_size AS suggested_order_qty
FROM positions WHERE inventory_position < reorder_point
ORDER BY store_id,product_id"""

RELIABILITY = """WITH due AS (
    SELECT po.supplier_id,COUNT(*) AS deliveries_due,
           SUM(CASE WHEN d.received_at <= d.promised_at AND d.received_at < '2026-07-01' THEN 1 ELSE 0 END) AS on_time_deliveries
    FROM deliveries d JOIN purchase_orders po ON po.purchase_order_id=d.purchase_order_id
    WHERE d.status <> 'CANCELLED' AND d.promised_at >= '2026-04-01' AND d.promised_at < '2026-07-01'
    GROUP BY po.supplier_id
)
SELECT s.supplier_id,s.supplier_name,COALESCE(d.deliveries_due,0) AS deliveries_due,
       COALESCE(d.on_time_deliveries,0) AS on_time_deliveries,
       COALESCE(d.deliveries_due-d.on_time_deliveries,0) AS late_or_unreceived,
       ROUND(100.0*d.on_time_deliveries/NULLIF(d.deliveries_due,0),2) AS on_time_pct
FROM suppliers s LEFT JOIN due d ON d.supplier_id=s.supplier_id
ORDER BY on_time_pct DESC,s.supplier_id"""

RECONCILIATION = """WITH opening AS (
    SELECT s.store_id,s.product_id,s.on_hand AS snapshot_qty,
           COALESCE(SUM(m.quantity),0) AS opening_qty
    FROM stock s LEFT JOIN stock_movements m
      ON m.store_id=s.store_id AND m.product_id=s.product_id AND m.occurred_at < '2026-06-01'
    GROUP BY s.store_id,s.product_id,s.on_hand
), running AS (
    SELECT m.store_id,m.product_id,
           o.opening_qty + SUM(m.quantity) OVER (
               PARTITION BY m.store_id,m.product_id ORDER BY m.occurred_at,m.movement_id
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS balance_qty
    FROM stock_movements m JOIN opening o ON o.store_id=m.store_id AND o.product_id=m.product_id
    WHERE m.occurred_at >= '2026-06-01' AND m.occurred_at < '2026-07-01'
), closing AS (
    SELECT s.store_id,s.product_id,COALESCE(SUM(m.quantity),0) AS ledger_closing_qty
    FROM stock s LEFT JOIN stock_movements m
      ON m.store_id=s.store_id AND m.product_id=s.product_id AND m.occurred_at < '2026-07-01'
    GROUP BY s.store_id,s.product_id
), balances AS (
    SELECT o.store_id,o.product_id,c.ledger_closing_qty,o.snapshot_qty,
           o.snapshot_qty-c.ledger_closing_qty AS difference_qty,
           LEAST(o.opening_qty,COALESCE(MIN(r.balance_qty),o.opening_qty)) AS minimum_balance
    FROM opening o JOIN closing c ON c.store_id=o.store_id AND c.product_id=o.product_id
    LEFT JOIN running r ON r.store_id=o.store_id AND r.product_id=o.product_id
    GROUP BY o.store_id,o.product_id,c.ledger_closing_qty,o.snapshot_qty,o.opening_qty
)
SELECT store_id,product_id,ledger_closing_qty,snapshot_qty,difference_qty,minimum_balance
FROM balances WHERE difference_qty <> 0 OR minimum_balance < 0
ORDER BY store_id,product_id"""

REORDER_QUANTITY = """CREATE FUNCTION reorder_quantity(
    p_on_hand INT,p_reserved INT,p_inbound INT,p_reorder_point INT,p_target INT,p_pack_size INT
) RETURNS BIGINT
DETERMINISTIC NO SQL SQL SECURITY INVOKER
BEGIN
    DECLARE v_position BIGINT;
    DECLARE v_shortfall BIGINT;
    IF p_on_hand IS NULL OR p_reserved IS NULL OR p_inbound IS NULL
       OR p_reorder_point IS NULL OR p_target IS NULL OR p_pack_size IS NULL
       OR p_on_hand < 0 OR p_reserved < 0 OR p_inbound < 0
       OR p_reorder_point < 0 OR p_target < 0 OR p_pack_size <= 0
       OR p_target < p_reorder_point THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_ARGUMENT';
    END IF;
    SET v_position=CAST(p_on_hand AS SIGNED)-p_reserved+p_inbound;
    IF v_position >= p_reorder_point THEN RETURN 0; END IF;
    SET v_shortfall=GREATEST(CAST(p_target AS SIGNED)-v_position,0);
    RETURN ((v_shortfall+p_pack_size-1) DIV p_pack_size)*p_pack_size;
END"""


def build_challenges(challenge):
    return [
        challenge("BI-Q01", "Build an actionable replenishment list", "inventory", "query", "Intermediate",
            "Buyers need to cover reservations without ordering units that are already on the way.",
            "Combine stock and purchase-order measures at their correct grains and round orders to complete packs.",
            ["Report immediately before 2026-07-01 00:00:00 UTC. stock.on_hand is the supplied snapshot. Available quantity = on_hand - reserved; retain negative availability.",
             "For each purchase-order line whose order was created strictly before the cutoff, received quantity is the sum of its delivery lines only when the delivery is RECEIVED and received_at is strictly before the cutoff. Scheduled, cancelled and later receipts do not reduce inbound.",
             "Open inbound is GREATEST(ordered_qty - cancelled_qty - received quantity, 0) for each purchase-order line, then summed by destination store/product. Floor each line independently, including legacy over-received lines. A product/store with no matching orders has zero inbound.",
             "Inventory position = available quantity + inbound quantity. Include only positions strictly below reorder_point. Suggested quantity is max(target_qty - position, 0), rounded up to a whole product pack_size multiple. Do not require the BI-F01 function.",
             "Return store_id, product_id, available_qty, inbound_qty, inventory_position, suggested_order_qty; order by store_id then product_id."],
            ["Stock, order lines and delivery lines are different grains. First count each received unit once, then each open order line once.",
             "Have you considered separate receipt and inbound aggregates, COALESCE(), GREATEST() and CEIL() or integer pack arithmetic?",
             "For non-negative whole-unit shortfall: ((shortfall + pack_size - 1) DIV pack_size) * pack_size rounds up exactly. Apply the reorder trigger separately."],
            "-- Explore inventory positions. Add cutoff-aware open inbound and pack rounding.\nSELECT store_id, product_id, on_hand - reserved AS available_qty\nFROM stock\nORDER BY store_id, product_id;",
            ["store_id", "product_id", "available_qty", "inbound_qty", "inventory_position", "suggested_order_qty"],
            ready=True, version="1.1.0", solution=REPLENISHMENT,
            query_feedback="Check receipt cutoff/state, per-line inbound floors, reservations, strict reorder boundaries and pack rounding.",
            explanation="Aggregate received quantities per purchase-order line before joining to ordered quantities. Otherwise several deliveries multiply the order quantity. Floor each line before summing so a legacy over-receipt cannot cancel an unrelated open line. Preserve negative available stock: reservations still need coverage. A stock-level correlated subquery is equally valid. Integer ceiling division avoids decimal division losing a tiny remainder for large whole-unit quantities."),
        challenge("BI-Q02", "Compare supplier delivery reliability", "inventory", "query", "Intermediate–advanced",
            "Procurement wants a fair comparison that includes batches that were due but have not arrived.",
            "Define a batch-level denominator, assess historical timestamps and retain suppliers with no eligible deliveries.",
            ["Include every supplier. Eligible deliveries are non-CANCELLED batches promised in [2026-04-01 00:00:00, 2026-07-01 00:00:00) UTC, linked through purchase_orders.supplier_id.",
             "A batch is on time only if received_at <= promised_at and received_at < 2026-07-01 00:00:00. Use timestamps for historical receipt assessment, rather than treating current RECEIVED status as proof it arrived before cutoff.",
             "Count every eligible delivery once regardless of its line count or quantity. late_or_unreceived = deliveries_due - on_time_deliveries.",
             "For suppliers with no eligible batches, return zero counts and NULL on_time_pct. Otherwise percentage = on-time count / due count * 100 rounded to two decimals. Supplier names need not be unique.",
             "Return supplier_id, supplier_name, deliveries_due, on_time_deliveries, late_or_unreceived, on_time_pct; order percentage descending (NULL last), then supplier_id ascending."],
            ["Choose the eligible delivery batches before calculating a percentage. Missing receipts still belong in the denominator.",
             "Have you thought about conditional aggregation, a LEFT JOIN from suppliers and NULLIF() for an empty denominator?",
             "One classification is CASE WHEN received_at <= promised_at AND received_at < '2026-07-01' THEN 1 ELSE 0 END. Keep this at delivery grain."],
            "-- Count eligible batches without joining delivery lines. Add on-time classification and suppliers with none.\nSELECT po.supplier_id, COUNT(*) AS deliveries_due\nFROM deliveries d JOIN purchase_orders po ON po.purchase_order_id = d.purchase_order_id\nWHERE d.status <> 'CANCELLED'\n  AND d.promised_at >= '2026-04-01' AND d.promised_at < '2026-07-01'\nGROUP BY po.supplier_id;",
            ["supplier_id", "supplier_name", "deliveries_due", "on_time_deliveries", "late_or_unreceived", "on_time_pct"],
            ready=True, version="1.1.0", solution=RELIABILITY,
            query_feedback="Check eligible batch counts, unreceived/after-cutoff deliveries, exact promise timestamps, supplier identities and NULL percentages.",
            explanation="Every scheduled batch is one reliability observation; joining lines first changes its weight. A receipt at the promised instant is on time, while receipts at or after the reporting cutoff are unreceived for this report. Start from suppliers to keep suppliers with no due batches and preserve NULL percentages instead of inventing a zero success rate. Correlated batch counts or conditional aggregation over a filtered LEFT JOIN are equally valid."),
        challenge("BI-Q03", "Reconcile the stock movement ledger", "inventory", "query", "Advanced",
            "Operations needs to find incorrect stock snapshots and shortages hidden by later recovery.",
            "Compute stable event-level balances, retain the opening balance and compare derived state with a snapshot.",
            ["For every existing stock row, opening balance is the sum of signed stock_movements.quantity strictly before 2026-06-01 00:00:00 UTC; no movements means zero.",
             "Process movements in [2026-06-01 00:00:00, 2026-07-01 00:00:00) in ascending (occurred_at, movement_id) order. All signed movement types count. Events exactly at July cutoff do not count.",
             "Ledger closing quantity is opening plus all June quantities. Minimum balance includes the opening balance and the balance after every June movement, even when no June movements exist.",
             "stock.on_hand is the supplied reporting-cutoff snapshot. Return rows only when snapshot differs from ledger closing, or minimum balance is negative. difference_qty = snapshot minus ledger closing.",
             "Return store_id, product_id, ledger_closing_qty, snapshot_qty, difference_qty, minimum_balance; order by store_id then product_id."],
            ["A final sum cannot reveal a shortage that was repaired. You need the balance after each event and the balance before the first event.",
             "Have you considered SUM() OVER with a ROWS frame and deterministic ordering by timestamp plus movement_id?",
             "An event prefix can use SUM(quantity) OVER (PARTITION BY store_id, product_id ORDER BY occurred_at, movement_id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW). Add the opening balance before taking the minimum."],
            "-- Inspect deterministic event order, then derive opening, running and closing balances.\nSELECT store_id, product_id, movement_id, occurred_at, quantity\nFROM stock_movements\nWHERE occurred_at < '2026-07-01'\nORDER BY store_id, product_id, occurred_at, movement_id;",
            ["store_id", "product_id", "ledger_closing_qty", "snapshot_qty", "difference_qty", "minimum_balance"],
            ready=True, version="1.1.0", solution=RECONCILIATION,
            query_feedback="Check opening balances, event order at tied timestamps, temporary negatives, no-event stocks and exclusive July cutoff.",
            explanation="Build one opening balance per stock row, then add a running June sum ordered by timestamp and movement ID. Include the opening itself in the minimum: a negative opening remains a shortage even if the first receipt repairs it. LEFT JOINs preserve stocks without June events. Closing and minimum answer different questions; their comparison with the snapshot finds both accounting mismatches and temporary negative balances. A correlated sum of each event prefix also works without window functions."),
        challenge("BI-F01", "Calculate pack-sized replenishment quantities", "inventory", "function", "Intermediate",
            "A purchasing integration needs a reusable reorder calculation that respects reservations and pack sizes.",
            "Separate the reorder trigger from order sizing and calculate exactly over the full signed INT input domain.",
            ["Define reorder_quantity(p_on_hand INT, p_reserved INT, p_inbound INT, p_reorder_point INT, p_target INT, p_pack_size INT) RETURNS BIGINT, SQL SECURITY INVOKER. It is a pure calculation: no table reads or mutations.",
             "All six inputs must be non-NULL. The first five inputs must be non-negative, pack_size must be strictly positive and target must be at least reorder_point. Every invalid argument signals SQLSTATE '45000' with MESSAGE_TEXT = 'INVALID_ARGUMENT'.",
             "Valid inputs range up to signed INT maximum 2147483647. Reservations may exceed on-hand. Calculate inventory position = on_hand - reserved + inbound with enough intermediate precision; negative derived positions are valid.",
             "Return zero when inventory position is at least reorder_point. Otherwise return max(target - position, 0) rounded UP to a whole pack multiple. The result may exceed signed INT maximum, so return BIGINT and avoid imprecise division.",
             "Submit the CREATE FUNCTION definition and optional DROP FUNCTION IF EXISTS; DELIMITER $$ or // is supported. For practice after defining it: SELECT reorder_quantity(2,8,0,10,25,6) AS reorder_quantity; returns 36."],
            ["First validate the inputs. Then decide whether to reorder. Only after that calculate how many whole packs reach the target.",
             "Have you considered BIGINT local variables and integer ceiling division? CEIL() works only if the preceding division retains a small nonzero remainder.",
             "For whole non-negative shortfall, ((shortfall + pack_size - 1) DIV pack_size) * pack_size rounds up exactly. Do not clamp a negative inventory position to zero."],
            "DELIMITER $$\nCREATE FUNCTION reorder_quantity(\n    p_on_hand INT, p_reserved INT, p_inbound INT,\n    p_reorder_point INT, p_target INT, p_pack_size INT\n) RETURNS BIGINT\nDETERMINISTIC NO SQL SQL SECURITY INVOKER\nBEGIN\n    -- Validate inputs, apply the reorder trigger and return whole packs.\n    RETURN 0;\nEND$$\nDELIMITER ;",
            ["reorder_quantity"], ready=True, version="1.1.0", routine_name="reorder_quantity", solution=REORDER_QUANTITY,
            explanation="Reservations exceeding on-hand create a valid negative position, increasing the shortfall. At the trigger itself no order is needed. BIGINT intermediates support adding or subtracting valid INT inputs and returning more than an INT. Integer ceiling division is exact even when a large pack size would make a small remainder disappear in MySQL's default decimal division scale. A sufficiently precise DECIMAL calculation with CEIL is another valid approach. Check every input before either returning zero or sizing an order."),
    ]


def routine_probes(challenge_id, variant):
    if challenge_id != "BI-F01":
        return []
    cases = [
        ((10, 0, 0, 10, 30, 6), "Exact reorder boundary"),
        ((11, 0, 0, 10, 30, 6), "Above reorder boundary"),
        ((9, 0, 0, 10, 30, 6), "Whole-pack ceiling"),
        ((0, 0, 0, 10, 30, 6), "Exact pack multiple"),
        ((0, 0, 0, 1, 1, 6), "One-unit shortfall"),
        ((2, 8, 0, 10, 25, 6), "Reservations exceed on-hand"),
        ((2, 8, 20, 10, 25, 6), "Inbound avoids reorder"),
        ((0, 0, 0, 0, 0, 1), "Zero target at trigger"),
        ((0, 1, 0, 0, 0, 1), "Zero target with negative position"),
        ((9, 0, 0, 10, 10, 4), "Target equals trigger"),
        ((2147483647, 0, 2147483647, 1, 2147483647, 1), "Large position intermediate"),
        ((0, 2147483647, 0, 1, 2147483647, 1), "Result exceeds INT"),
        ((0, 2147483647, 0, 1, 1, 2147483647), "Tiny pack-division remainder"),
        ((0, 2147483647, 0, 1, 2147483647, 2147483646), "Large rounded result"),
        ((1 + variant, 9, 0, 10, 28 + variant, 5 + variant), "Independent valid arithmetic"),
        ((0, 0, 0, 1, 1, 0), "Zero pack size"),
        ((0, 0, 0, 10, 9, 1), "Target below reorder point"),
    ]
    valid = (5, 1, 2, 10, 30, 6)
    for index, name in enumerate(("on-hand", "reserved", "inbound", "reorder point", "target", "pack size")):
        values = list(valid)
        values[index] = None
        cases.append((tuple(values), f"NULL {name}"))
        values[index] = -1
        cases.append((tuple(values), f"Negative {name}"))
    return [("SELECT reorder_quantity(" + ",".join("NULL" if value is None else str(value) for value in values) + ") AS reorder_quantity", label)
            for values, label in cases]
