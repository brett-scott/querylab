INACTIVE_CUSTOMERS = """WITH refund_totals AS (
 SELECT order_item_id, SUM(amount) AS amount FROM refunds
 WHERE status='POSTED' AND refunded_at < '2026-07-01' GROUP BY order_item_id
), customer_totals AS (
 SELECT c.customer_id,c.customer_name,
 SUM(oi.quantity*oi.unit_price-COALESCE(r.amount,0)) AS net_spending,
 MAX(o.completed_at) AS last_completed_order_at
 FROM customers c JOIN orders o ON o.customer_id=c.customer_id
 JOIN order_items oi ON oi.order_id=o.order_id
 LEFT JOIN refund_totals r ON r.order_item_id=oi.order_item_id
 WHERE o.status='COMPLETED' AND o.completed_at < '2026-07-01'
 GROUP BY c.customer_id,c.customer_name
)
SELECT customer_id,customer_name,net_spending,last_completed_order_at
FROM customer_totals WHERE net_spending >= 500
AND last_completed_order_at < DATE_SUB('2026-07-01', INTERVAL 90 DAY)
ORDER BY net_spending DESC,customer_id"""

LOYALTY_TIER = """CREATE FUNCTION loyalty_tier(p_net_spend DECIMAL(12,2))
RETURNS VARCHAR(10) DETERMINISTIC NO SQL SQL SECURITY INVOKER
BEGIN
 IF p_net_spend IS NULL THEN RETURN NULL; END IF;
 IF p_net_spend < 0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_SPEND'; END IF;
 RETURN CASE WHEN p_net_spend < 500 THEN 'STANDARD'
 WHEN p_net_spend < 2000 THEN 'SILVER' WHEN p_net_spend < 5000 THEN 'GOLD' ELSE 'PLATINUM' END;
END"""

ISSUE_REFUND = """CREATE PROCEDURE issue_refund(
 IN p_request_key VARCHAR(64), IN p_order_item_id BIGINT,
 IN p_payment_id BIGINT, IN p_amount DECIMAL(12,2), IN p_refunded_at DATETIME)
SQL SECURITY INVOKER
main: BEGIN
 DECLARE v_item_value DECIMAL(12,2);
 DECLARE v_payment_value DECIMAL(12,2);
 DECLARE v_item_used DECIMAL(12,2);
 DECLARE v_payment_used DECIMAL(12,2);
 DECLARE v_order_id BIGINT;
 DECLARE v_payment_order_id BIGINT;
 DECLARE v_completed_at DATETIME;
 DECLARE v_captured_at DATETIME;
 DECLARE v_order_status VARCHAR(20);
 DECLARE v_payment_status VARCHAR(20);
 DECLARE v_refund_id BIGINT;
 DECLARE v_old_item BIGINT;
 DECLARE v_old_payment BIGINT;
 DECLARE v_old_amount DECIMAL(12,2);
 DECLARE v_old_at DATETIME;
 DECLARE v_old_remaining DECIMAL(12,2);
 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
 IF p_request_key IS NULL OR LENGTH(TRIM(p_request_key))=0 OR p_order_item_id IS NULL
 OR p_payment_id IS NULL OR p_amount IS NULL OR p_amount<=0 OR p_refunded_at IS NULL THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_ARGUMENT'; END IF;
 START TRANSACTION;
 SELECT MAX(refund_id) INTO v_refund_id FROM refunds WHERE request_key=p_request_key;
 IF v_refund_id IS NOT NULL THEN
 SELECT order_item_id,payment_id,amount,refunded_at,item_remaining_refundable
 INTO v_old_item,v_old_payment,v_old_amount,v_old_at,v_old_remaining FROM refunds WHERE refund_id=v_refund_id;
 IF v_old_item<>p_order_item_id OR v_old_payment<>p_payment_id OR v_old_amount<>p_amount OR v_old_at<>p_refunded_at THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='REQUEST_CONFLICT'; END IF;
 COMMIT;
 SELECT v_refund_id AS refund_id,v_old_amount AS refunded_amount,v_old_remaining AS item_remaining_refundable;
 LEAVE main;
 END IF;
 IF NOT EXISTS(SELECT 1 FROM order_items WHERE order_item_id=p_order_item_id)
 OR NOT EXISTS(SELECT 1 FROM payments WHERE payment_id=p_payment_id) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='RECORD_NOT_FOUND'; END IF;
 SELECT i.quantity*i.unit_price,i.order_id,o.completed_at,o.status
 INTO v_item_value,v_order_id,v_completed_at,v_order_status
 FROM order_items i JOIN orders o ON o.order_id=i.order_id WHERE i.order_item_id=p_order_item_id FOR UPDATE;
 SELECT amount,order_id,captured_at,status INTO v_payment_value,v_payment_order_id,v_captured_at,v_payment_status
 FROM payments WHERE payment_id=p_payment_id FOR UPDATE;
 IF v_order_status<>'COMPLETED' OR v_payment_status<>'SUCCESS' OR v_order_id<>v_payment_order_id THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_ORDER_PAYMENT'; END IF;
 IF p_refunded_at<v_completed_at OR p_refunded_at<v_captured_at THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_TIMESTAMP'; END IF;
 SELECT COALESCE(SUM(amount),0) INTO v_item_used FROM refunds WHERE order_item_id=p_order_item_id AND status='POSTED';
 SELECT COALESCE(SUM(amount),0) INTO v_payment_used FROM refunds WHERE payment_id=p_payment_id AND status='POSTED';
 IF p_amount>v_item_value-v_item_used OR p_amount>v_payment_value-v_payment_used THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='REFUND_LIMIT_EXCEEDED'; END IF;
 UPDATE payments SET refunded_amount=v_payment_used+p_amount WHERE payment_id=p_payment_id;
 INSERT INTO refunds(request_key,order_item_id,payment_id,amount,status,refunded_at,item_remaining_refundable)
 VALUES(p_request_key,p_order_item_id,p_payment_id,p_amount,'POSTED',p_refunded_at,v_item_value-v_item_used-p_amount);
 SET v_refund_id=LAST_INSERT_ID();
 COMMIT;
 SELECT v_refund_id AS refund_id,p_amount AS refunded_amount,v_item_value-v_item_used-p_amount AS item_remaining_refundable;
END"""
