from . import solutions


def challenge(id, title, dataset, kind, difficulty, scenario, objective, requirements, hints, starter, columns, *, ready=False, solution="", explanation="", version="1.0.0", routine_name=None, query_feedback=None):
    return dict(id=id,title=title,dataset=dataset,dataset_name="Online store" if dataset=="online-store" else "Business / inventory",
                type=kind,difficulty=difficulty,summary=scenario,scenario=scenario,objective=objective,
                requirements=requirements,hints=hints,starter_sql=starter,expected_columns=columns,
                ready=ready,version=version,solution=solution,explanation=explanation,
                routine_name=routine_name,query_feedback=query_feedback)


CHALLENGES = [
challenge("OS-Q01","Recover inactive high-value customers","online-store","query","Intermediate",
 "Marketing needs a defensible list of valuable customers who have stopped ordering, without targeting people whose purchases were mostly refunded.",
 "Aggregate at the correct grain, separate lifetime value from recent activity, and apply precise date boundaries.",
 ["Use reporting cutoff 2026-07-01 00:00:00 UTC, exclusive. Use item quantity × sale-time unit_price for sales, not payment totals.",
  "For completed orders before the cutoff, sum item sales minus POSTED refunds strictly before the cutoff. Pending/failed refunds do not reduce spending.",
  "Include net spending of at least 500.00 and no completed order in [2026-04-02 00:00:00, 2026-07-01 00:00:00). A fully refunded recent order still counts as activity.",
  "Exclude customers with no eligible orders. Group by customer_id; names need not be unique.",
  "Return customer_id, customer_name, net_spending, last_completed_order_at. Sort net_spending descending, then customer_id ascending."],
 ["Lifetime spending and recent activity answer different questions. Aggregate refunds before joining them to item sales.",
  "Have you considered a CTE for refund totals and MAX(completed_at) or NOT EXISTS for inactivity?",
  "Start with: SELECT order_item_id, SUM(amount) AS refunded FROM refunds WHERE status = 'POSTED' AND refunded_at < '2026-07-01' GROUP BY order_item_id;"],
 "-- Explore completed-order activity before the reporting cutoff.\n-- Add refund-adjusted spending and inactivity rules to solve the challenge.\nSELECT\n    c.customer_id,\n    c.customer_name,\n    MAX(o.completed_at) AS last_completed_order_at\nFROM customers c\nJOIN orders o ON o.customer_id = c.customer_id\nWHERE o.status = 'COMPLETED'\n  AND o.completed_at < '2026-07-01'\nGROUP BY c.customer_id, c.customer_name\nORDER BY c.customer_id;",
 ["customer_id","customer_name","net_spending","last_completed_order_at"],ready=True,solution=solutions.INACTIVE_CUSTOMERS,
 explanation="Aggregate refunds once per item before joining sales, so several payments or refunds cannot multiply revenue. The latest eligible completed-order timestamp tests inactivity even when that order was fully refunded. Preserve customer IDs because names are not unique. A correlated NOT EXISTS test for recent completed orders is equally valid."),
challenge("OS-F01","Apply consistent loyalty tiers","online-store","function","Intermediate",
 "Different reports classify customers differently. Build one reusable function that applies a consistent spending policy.",
 "Write a stored function with precise NULL, boundary and invalid-input behavior.",
 ["Define loyalty_tier(p_net_spend DECIMAL(12,2)) RETURNS VARCHAR(10). Use SQL SECURITY INVOKER. No table reads or changes are needed.",
  "Return STANDARD for [0,500), SILVER for [500,2000), GOLD for [2000,5000), and PLATINUM for 5000 or more.",
  "NULL input returns NULL. Negative input must SIGNAL SQLSTATE '45000' with MESSAGE_TEXT = 'INVALID_SPEND'.",
  "Submit the complete CREATE FUNCTION definition; optional DROP FUNCTION IF EXISTS is accepted. DELIMITER $$ or // client directives are supported. The grader calls your function."],
 ["Write the boundary values down first. Unknown spending and invalid negative spending need different behavior.","Have you thought about CASE, early RETURN and SIGNAL SQLSTATE '45000'?","One branch could be: WHEN p_net_spend < 500 THEN 'STANDARD'. Check NULL and negatives before classifying."],
 "DELIMITER $$\nCREATE FUNCTION loyalty_tier(p_net_spend DECIMAL(12,2))\nRETURNS VARCHAR(10)\nDETERMINISTIC NO SQL SQL SECURITY INVOKER\nBEGIN\n    -- Validate and return the appropriate tier.\n    RETURN NULL;\nEND$$\nDELIMITER ;",
 ["loyalty_tier"],ready=True,solution=solutions.LOYALTY_TIER,
 explanation="Check NULL before numeric boundaries, and reject negative spending explicitly. Ordered upper-bound branches handle exact thresholds without gaps or overlaps. DETERMINISTIC NO SQL describes a pure calculation. A sequence of IF/RETURN statements is also correct."),
challenge("OS-P01","Record a refund without exceeding payment","online-store","procedure","Advanced",
 "Customer service needs to issue partial refunds safely. A retried request must return its original result without creating another refund.",
 "Combine cumulative validation, transaction ownership, rollback and idempotent requests.",
 ["Define issue_refund(p_request_key VARCHAR(64), p_order_item_id BIGINT, p_payment_id BIGINT, p_amount DECIMAL(12,2), p_refunded_at DATETIME), SQL SECURITY INVOKER. Calls are top-level and serialized in each learner workspace.",
  "Reject NULL inputs, blank request keys and non-positive amounts with SQLSTATE 45000 / INVALID_ARGUMENT. Missing item/payment: RECORD_NOT_FOUND.",
  "The item and SUCCESS payment must belong to the same COMPLETED order, otherwise INVALID_ORDER_PAYMENT. Refund time must be at or after order completion and payment capture, otherwise INVALID_TIMESTAMP.",
  "Count all POSTED refunds independently against item value (quantity × unit_price) and payment amount. Exceeding either remaining budget raises REFUND_LIMIT_EXCEEDED.",
  "Maintain payments.refunded_amount as the total of POSTED refunds for that payment. Update this summary before inserting the refund, within the same transaction. If the insert fails, the summary must roll back too. Do not change other payment fields.",
  "Insert exactly one POSTED refund with request_key, order_item_id, payment_id, amount, refunded_at and original item_remaining_refundable. Same key/payload returns the original result; changed payload raises REQUEST_CONFLICT.",
  "Return one row: refund_id, refunded_amount, item_remaining_refundable. All documented validation errors use SQLSTATE 45000 and the exact message. On unexpected database failures rollback and propagate the error. Business tables must otherwise remain unchanged.",
  "Submit only the routine definition and optional DROP PROCEDURE IF EXISTS. Run may include a CALL after defining it. Example valid practice call: CALL issue_refund('practice-1', 1, 1, 25.00, '2026-06-30 12:00:00');"],
 ["Treat the item budget, payment budget and request replay as separate checks. A failure must undo the entire operation.","Have you considered START TRANSACTION, SELECT ... FOR UPDATE and an EXIT HANDLER that rolls back and RESIGNALs?","A handler can start: DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END; Store the original remaining value to make retries stable."],
 "DELIMITER $$\nCREATE PROCEDURE issue_refund(\n    IN p_request_key VARCHAR(64),\n    IN p_order_item_id BIGINT,\n    IN p_payment_id BIGINT,\n    IN p_amount DECIMAL(12,2),\n    IN p_refunded_at DATETIME\n)\nSQL SECURITY INVOKER\nBEGIN\n    -- Add transaction handling, validation and retry protection.\n    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'NOT_IMPLEMENTED';\nEND$$\nDELIMITER ;",
 ["refund_id","refunded_amount","item_remaining_refundable"],ready=True,solution=solutions.ISSUE_REFUND,
 explanation="A request key identifies an operation, so replay must return the first operation's result even if later refunds changed its balance. Lock the item and payment rows and aggregate their posted refunds separately. Update the payment's refunded_amount summary before inserting the refund, then commit both together. The exception handler rolls back the summary if the insert fails. QueryLab serializes jobs per workspace; overlapping calls to this routine are outside the current exercise contract."),
]

# Authored executable specifications; references remain behind explicit solution reveal.
from .online_expansion import build_challenges as online_challenges
from .inventory_expansion import build_challenges as inventory_challenges
from .inventory_procedures import build_challenges as inventory_procedure_challenges

CHALLENGES.extend(online_challenges(challenge))
CHALLENGES.extend(inventory_challenges(challenge))
CHALLENGES.extend(inventory_procedure_challenges(challenge))

BY_ID = {c["id"]:c for c in CHALLENGES}


def public(challenge):
    return {k:v for k,v in challenge.items() if k not in {"solution","explanation","query_feedback"}}
