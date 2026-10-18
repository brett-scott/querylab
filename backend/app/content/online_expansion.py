"""Authored online-store reporting and historical-spending exercises."""

MONTHLY_NET_SALES = """WITH item_refunds AS (
 SELECT order_item_id,SUM(amount) AS refunded
 FROM refunds WHERE status='POSTED' AND refunded_at<'2026-07-01'
 GROUP BY order_item_id
), monthly_sales AS (
 SELECT CAST(DATE_FORMAT(o.completed_at,'%Y-%m-01') AS DATE) AS month_start,
 SUM(i.quantity*i.unit_price-COALESCE(r.refunded,0)) AS net_sales
 FROM orders o JOIN order_items i ON i.order_id=o.order_id
 LEFT JOIN item_refunds r ON r.order_item_id=i.order_item_id
 WHERE o.status='COMPLETED' AND o.completed_at>='2026-01-01' AND o.completed_at<'2026-07-01'
 GROUP BY CAST(DATE_FORMAT(o.completed_at,'%Y-%m-01') AS DATE)
), complete_months AS (
 SELECT c.month_start,COALESCE(s.net_sales,0.00) AS net_sales
 FROM calendar_months c LEFT JOIN monthly_sales s ON s.month_start=c.month_start
 WHERE c.month_start>='2026-01-01' AND c.month_start<'2026-07-01'
), compared AS (
 SELECT month_start,net_sales,
 SUM(net_sales) OVER (ORDER BY month_start ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_net_sales,
 LAG(net_sales) OVER (ORDER BY month_start) AS previous_net_sales
 FROM complete_months
)
SELECT month_start,net_sales,running_net_sales,
 ROUND((net_sales-previous_net_sales)/NULLIF(previous_net_sales,0)*100,2) AS month_over_month_pct
FROM compared ORDER BY month_start"""

LEADING_PRODUCTS = """WITH item_refunds AS (
 SELECT order_item_id,SUM(amount) AS refunded FROM refunds
 WHERE status='POSTED' AND refunded_at<'2026-07-01' GROUP BY order_item_id
), product_sales AS (
 SELECT i.category_id,i.product_id,SUM(i.quantity*i.unit_price-COALESCE(r.refunded,0)) AS net_sales
 FROM orders o JOIN order_items i ON i.order_id=o.order_id
 LEFT JOIN item_refunds r ON r.order_item_id=i.order_item_id
 WHERE o.status='COMPLETED' AND o.completed_at>='2026-04-01' AND o.completed_at<'2026-07-01'
 GROUP BY i.category_id,i.product_id
 HAVING SUM(i.quantity*i.unit_price-COALESCE(r.refunded,0))>0
), ranked AS (
 SELECT category_id,product_id,net_sales,
 DENSE_RANK() OVER (PARTITION BY category_id ORDER BY net_sales DESC) AS revenue_rank
 FROM product_sales
)
SELECT r.category_id,r.product_id,p.product_name,r.net_sales,r.revenue_rank
FROM ranked r JOIN products p ON p.product_id=r.product_id
WHERE r.revenue_rank<=2 ORDER BY r.category_id,r.revenue_rank,r.product_id"""

CUSTOMER_NET_SPEND = """CREATE FUNCTION customer_net_spend(p_customer_id BIGINT,p_cutoff DATETIME)
RETURNS DECIMAL(12,2) READS SQL DATA SQL SECURITY INVOKER
BEGIN
 DECLARE v_spend DECIMAL(12,2);
 IF p_customer_id IS NULL OR p_cutoff IS NULL THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_ARGUMENT'; END IF;
 IF NOT EXISTS(SELECT 1 FROM customers WHERE customer_id=p_customer_id) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='CUSTOMER_NOT_FOUND'; END IF;
 SELECT COALESCE(SUM(i.quantity*i.unit_price-COALESCE(r.refunded,0)),0.00) INTO v_spend
 FROM orders o JOIN order_items i ON i.order_id=o.order_id
 LEFT JOIN (
   SELECT order_item_id,SUM(amount) AS refunded FROM refunds
   WHERE status='POSTED' AND refunded_at<p_cutoff GROUP BY order_item_id
 ) r ON r.order_item_id=i.order_item_id
 WHERE o.customer_id=p_customer_id AND o.status='COMPLETED' AND o.completed_at<p_cutoff;
 RETURN v_spend;
END"""


def build_challenges(challenge):
    return [
        challenge("OS-Q02", "Build a monthly net-sales trend", "online-store", "query", "Intermediate–advanced",
            "Finance needs a six-month sales trend that includes quiet months and treats historical refunds consistently.",
            "Build a complete monthly series, aggregate at item grain and compare adjacent periods.",
            ["Report January through June 2026 using calendar_months, including months with no eligible sales. Restrict the calendar to [2026-01-01, 2026-07-01). All timestamps are UTC.",
             "Eligible sales are quantity × sale-time unit_price from COMPLETED orders in that period. Subtract only POSTED item refunds strictly before 2026-07-01 00:00:00; pending refunds and refunds at/after the cutoff do not count.",
             "Attribute each refund to its original order's completion month, even when the refund happened later. Payments are not sales and must not multiply item amounts.",
             "Return month_start (DATE), net_sales, running_net_sales and month_over_month_pct, ordered by month_start ascending. Missing monthly sales are 0.00; running_net_sales includes the current month.",
             "Growth is (current net sales − previous net sales) / previous net sales × 100, rounded to two decimals. January and any month whose previous sales are zero return NULL for growth."],
            ["Create exactly one row per reporting month before comparing adjacent months. Refunds belong to the order's month, not the refund's month.",
             "Have you considered a LEFT JOIN from calendar_months, then LAG() and a windowed SUM() over those complete monthly totals?",
             "After monthly aggregation: LAG(net_sales) OVER (ORDER BY month_start) AS previous_net_sales. NULLIF(previous_net_sales, 0) protects the growth denominator."],
            "-- Start with the complete reporting calendar; add refund-adjusted monthly sales.\nSELECT month_start\nFROM calendar_months\nWHERE month_start >= '2026-01-01' AND month_start < '2026-07-01'\nORDER BY month_start;",
            ["month_start", "net_sales", "running_net_sales", "month_over_month_pct"],
            ready=True, version="1.1.0", solution=MONTHLY_NET_SALES,
            query_feedback="Check zero-filled months, order-month refund attribution, exclusive cutoff, cumulative totals and NULL growth after zero sales.",
            explanation="Aggregate posted refunds per item first so multiple refunds cannot duplicate gross sales. Aggregate the resulting item net values by the order's completion month, then left join the reporting calendar and replace missing totals with zero. Only after there is one row per month should SUM and LAG calculate the running total and previous month. NULLIF makes both the first month and a zero baseline produce NULL growth. Correlated monthly aggregates or a self join to the preceding calendar month are equally valid alternatives."),
        challenge("OS-Q03", "Find the leading products in each category", "online-store", "query", "Intermediate–advanced",
            "Merchandising wants the first two revenue ranks in each category, including every tied product.",
            "Separate product aggregation from ranking and preserve business ties.",
            ["Use COMPLETED orders with completed_at in [2026-04-01 00:00:00, 2026-07-01 00:00:00), UTC. Item gross sales are quantity × sale-time unit_price.",
             "Subtract POSTED refunds for those items only when refunded_at is strictly before 2026-07-01. Ignore pending refunds and refunds at/after the cutoff; do not join payments into revenue.",
             "Aggregate by order_items.category_id and product_id. The item's category is its sale-time category; products.category_id may since have changed. Display the current products.product_name, keeping distinct product IDs even when names match.",
             "Exclude totals of zero or less. Assign dense revenue ranks separately within each sale-time category: ties share a rank, and the next distinct revenue gets the next consecutive rank. Return all products in ranks 1 and 2.",
             "Return category_id, product_id, product_name, net_sales and revenue_rank, ordered by category_id, revenue_rank and product_id ascending. Product ID breaks display ties only, never revenue ties."],
            ["Two revenue ranks may contain more than two products. Decide the aggregation grain before ranking.",
             "Have you thought about DENSE_RANK() partitioned by the item's category, ordered only by aggregate net sales descending?",
             "Over an already aggregated product result: DENSE_RANK() OVER (PARTITION BY category_id ORDER BY net_sales DESC). Filter the resulting rank in an outer query."],
            "-- Explore sale-time category/product totals, then account for refunds and revenue ties.\nSELECT i.category_id, i.product_id, SUM(i.quantity * i.unit_price) AS gross_sales\nFROM orders o\nJOIN order_items i ON i.order_id = o.order_id\nWHERE o.status = 'COMPLETED'\n  AND o.completed_at >= '2026-04-01' AND o.completed_at < '2026-07-01'\nGROUP BY i.category_id, i.product_id\nORDER BY i.category_id, i.product_id;",
            ["category_id", "product_id", "product_name", "net_sales", "revenue_rank"],
            ready=True, version="1.1.0", solution=LEADING_PRODUCTS,
            query_feedback="Check dense ties at both ranks, positive net sales, sale-time categories and refund eligibility before ordering the output.",
            explanation="Pre-aggregate eligible refunds per item, then sum net item sales by sale-time category and product ID. Remove non-positive product totals before ranking. DENSE_RANK counts distinct revenue levels; ROW_NUMBER arbitrarily discards ties, while RANK leaves gaps after ties. Adding product ID inside the ranking ORDER BY would destroy the ties. Join product names after aggregation, and use product ID only in the final display ordering. A correlated count of distinct higher revenue totals can implement the same dense-rank rule without a window function."),
        challenge("OS-F02", "Calculate customer net spending at a cutoff", "online-store", "function", "Intermediate–advanced",
            "Reports need one reusable function for a customer's historical spending, without confusing a missing customer with an empty purchase history.",
            "Read related tables at the correct grain and apply one parameterized exclusive cutoff.",
            ["Define customer_net_spend(p_customer_id BIGINT, p_cutoff DATETIME) RETURNS DECIMAL(12,2), with SQL SECURITY INVOKER. Read tables without changing business data; READS SQL DATA describes this function.",
             "For this customer, include only COMPLETED orders whose completed_at is strictly before p_cutoff. Gross sales use item quantity × sale-time unit_price; payment amounts are not sales.",
             "Subtract only POSTED refunds on eligible items whose refunded_at is also strictly before p_cutoff. Both boundaries are exclusive, in UTC. Use the supplied parameter, never the current time or a fixed report date.",
             "Return 0.00 for an existing customer without eligible sales, including a customer with no orders. Customer IDs identify people; names may be duplicated.",
             "If either input is NULL, SIGNAL SQLSTATE '45000' with MESSAGE_TEXT='INVALID_ARGUMENT'. Otherwise an unknown customer ID raises SQLSTATE '45000' / CUSTOMER_NOT_FOUND. Return one numeric value for valid inputs.",
             "Submit the complete CREATE FUNCTION definition, optionally preceded by DROP FUNCTION IF EXISTS. The grader supplies calls, including different historical cutoffs. Practice example: SELECT customer_net_spend(1, '2026-07-01') AS customer_net_spend;"],
            ["Customer existence is a separate question from whether any orders qualify. Keep refund amounts from multiplying item sales.",
             "Have you considered EXISTS for validation, an aggregate of posted refunds per item, and COALESCE(SUM(...), 0.00)?",
             "A validation branch can use IF NOT EXISTS (SELECT 1 FROM customers WHERE customer_id = p_customer_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='CUSTOMER_NOT_FOUND'; END IF;"],
            "DELIMITER $$\nCREATE FUNCTION customer_net_spend(p_customer_id BIGINT, p_cutoff DATETIME)\nRETURNS DECIMAL(12,2)\nREADS SQL DATA SQL SECURITY INVOKER\nBEGIN\n    -- Validate existence, then calculate spending at the supplied cutoff.\n    RETURN 0.00;\nEND$$\nDELIMITER ;",
            ["customer_net_spend"], ready=True, version="1.1.0", routine_name="customer_net_spend", solution=CUSTOMER_NET_SPEND,
            explanation="Validate NULL arguments before looking for a customer, then check existence independently of order aggregation. Pre-aggregate refunds per item at the supplied cutoff and subtract them once from each eligible item's sales. COALESCE handles an empty purchase history. Payment rows do not affect this sales calculation, and pending records do not become posted merely because their timestamp is old. This function reads changing business tables, so READS SQL DATA is appropriate. Two independent aggregates for sales and eligible refunds, or a correlated refund subquery per item, give the same result."),
    ]


def routine_probes(challenge_id, variant):
    if challenge_id != "OS-F02":
        raise ValueError("Unsupported online-store routine")
    shift = variant * 100
    def call(customer, cutoff, label):
        return (f"SELECT customer_net_spend({customer}, {cutoff}) AS customer_net_spend", label)
    probes = [call(i+shift, "'2026-07-01'", label) for i, label in [
        (1, "Several items, payments and refunds"), (2, "Pending order excluded"),
        (3, "Refund-adjusted recent sales"), (4, "Duplicate customer name"),
        (5, "Cancelled order excluded"), (6, "Exact order and refund cutoff"),
        (7, "Existing customer with one order"), (8, "Existing customer without orders")]]
    for cutoff, label in [
        ("2026-01-10 10:00:00", "Order exactly at parameter cutoff"),
        ("2026-01-10 10:00:01", "Order immediately before parameter cutoff"),
        ("2026-01-20 10:00:00", "Refund exactly at parameter cutoff"),
        ("2026-01-20 10:00:01", "Refund immediately before parameter cutoff"),
        ("2026-02-01 10:00:00", "Several refunds across historical cutoffs"),
        ("2026-02-10 10:00:01", "Item-specific refunds across payments"),
        ("2026-07-03", "Later parameter includes later completed orders"),
        ("1900-01-01", "Existing customer before first order")]:
        probes.append(call(1+shift, f"'{cutoff}'", label))
    probes.extend([
        call(6+shift, "'2026-07-01 00:00:01'", "Later cutoff includes newly eligible order and refund"),
        call(999999, "'2026-07-01'", "Unknown customer"),
        call(-1, "'2026-07-01'", "Negative unknown customer identifier"),
        call("NULL", "'2026-07-01'", "NULL customer identifier"),
        call(1+shift, "NULL", "NULL cutoff"),
        call(999999, "NULL", "NULL validation precedes customer lookup"),
        call("NULL", "NULL", "Both inputs NULL"),
    ])
    return probes
