"""Executable inventory procedure contracts and private grading cases."""

TRANSFER_STOCK = """CREATE PROCEDURE transfer_stock(
 IN p_request_key VARCHAR(64), IN p_product_id BIGINT, IN p_source_store_id BIGINT,
 IN p_destination_store_id BIGINT, IN p_quantity INT, IN p_occurred_at DATETIME)
SQL SECURITY INVOKER
main: BEGIN
 DECLARE v_transfer BIGINT;
 DECLARE v_product BIGINT;
 DECLARE v_source BIGINT;
 DECLARE v_destination BIGINT;
 DECLARE v_quantity INT;
 DECLARE v_at DATETIME;
 DECLARE v_source_on_hand BIGINT;
 DECLARE v_reserved BIGINT;
 DECLARE v_destination_on_hand BIGINT;
 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
 IF p_request_key IS NULL OR LENGTH(TRIM(p_request_key))=0 OR p_product_id IS NULL
 OR p_source_store_id IS NULL OR p_destination_store_id IS NULL OR p_quantity IS NULL
 OR p_occurred_at IS NULL OR p_product_id<=0 OR p_source_store_id<=0
 OR p_destination_store_id<=0 OR p_quantity<=0 OR p_source_store_id=p_destination_store_id THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_ARGUMENT'; END IF;
 START TRANSACTION;
 SELECT MAX(transfer_id) INTO v_transfer FROM transfers WHERE request_key=p_request_key;
 IF v_transfer IS NOT NULL THEN
 SELECT product_id,source_store_id,destination_store_id,quantity,occurred_at
 INTO v_product,v_source,v_destination,v_quantity,v_at FROM transfers WHERE transfer_id=v_transfer;
 IF v_product<>p_product_id OR v_source<>p_source_store_id OR v_destination<>p_destination_store_id
 OR v_quantity<>p_quantity OR v_at<>p_occurred_at THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='REQUEST_CONFLICT'; END IF;
 COMMIT;
 SELECT v_transfer AS transfer_id,v_quantity AS quantity_transferred,'COMPLETED' AS status;
 LEAVE main;
 END IF;
 IF NOT EXISTS(SELECT 1 FROM products WHERE product_id=p_product_id)
 OR NOT EXISTS(SELECT 1 FROM stores WHERE store_id=p_source_store_id)
 OR NOT EXISTS(SELECT 1 FROM stores WHERE store_id=p_destination_store_id)
 OR NOT EXISTS(SELECT 1 FROM stock WHERE product_id=p_product_id AND store_id=p_source_store_id)
 OR NOT EXISTS(SELECT 1 FROM stock WHERE product_id=p_product_id AND store_id=p_destination_store_id) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='RECORD_NOT_FOUND'; END IF;
 SELECT on_hand,reserved INTO v_source_on_hand,v_reserved FROM stock
 WHERE product_id=p_product_id AND store_id=p_source_store_id FOR UPDATE;
 SELECT on_hand INTO v_destination_on_hand FROM stock
 WHERE product_id=p_product_id AND store_id=p_destination_store_id FOR UPDATE;
 IF v_source_on_hand-v_reserved<p_quantity THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INSUFFICIENT_STOCK'; END IF;
 IF v_destination_on_hand+p_quantity>2147483647 THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='STOCK_OVERFLOW'; END IF;
 UPDATE stock SET on_hand=on_hand-p_quantity WHERE product_id=p_product_id AND store_id=p_source_store_id;
 UPDATE stock SET on_hand=on_hand+p_quantity WHERE product_id=p_product_id AND store_id=p_destination_store_id;
 INSERT INTO transfers(request_key,product_id,source_store_id,destination_store_id,quantity,occurred_at)
 VALUES(p_request_key,p_product_id,p_source_store_id,p_destination_store_id,p_quantity,p_occurred_at);
 SET v_transfer=LAST_INSERT_ID();
 INSERT INTO stock_movements(store_id,product_id,quantity,occurred_at,transfer_id)
 VALUES(p_source_store_id,p_product_id,-p_quantity,p_occurred_at,v_transfer),
 (p_destination_store_id,p_product_id,p_quantity,p_occurred_at,v_transfer);
 COMMIT;
 SELECT v_transfer AS transfer_id,p_quantity AS quantity_transferred,'COMPLETED' AS status;
END"""

RECEIVE_DELIVERY = """CREATE PROCEDURE receive_delivery(IN p_delivery_id BIGINT, IN p_received_at DATETIME)
SQL SECURITY INVOKER
main: BEGIN
 DECLARE v_done BOOLEAN DEFAULT FALSE;
 DECLARE v_po BIGINT;
 DECLARE v_store BIGINT;
 DECLARE v_created DATETIME;
 DECLARE v_status VARCHAR(20);
 DECLARE v_received DATETIME;
 DECLARE v_lines BIGINT;
 DECLARE v_units BIGINT;
 DECLARE v_line BIGINT;
 DECLARE v_product BIGINT;
 DECLARE v_quantity INT;
 DECLARE c_lines CURSOR FOR SELECT dl.delivery_line_id,pol.product_id,dl.quantity
 FROM delivery_lines dl JOIN purchase_order_lines pol USING(purchase_order_line_id)
 WHERE dl.delivery_id=p_delivery_id ORDER BY dl.delivery_line_id;
 DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done=TRUE;
 DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
 IF p_delivery_id IS NULL OR p_delivery_id<=0 OR p_received_at IS NULL THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_ARGUMENT'; END IF;
 START TRANSACTION;
 IF NOT EXISTS(SELECT 1 FROM deliveries WHERE delivery_id=p_delivery_id) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='DELIVERY_NOT_FOUND'; END IF;
 SELECT purchase_order_id,status,received_at,lines_received,units_received
 INTO v_po,v_status,v_received,v_lines,v_units FROM deliveries WHERE delivery_id=p_delivery_id FOR UPDATE;
 IF v_status='RECEIVED' THEN
 IF v_received IS NULL OR v_lines IS NULL OR v_units IS NULL OR v_lines<=0 OR v_units<=0 THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_DELIVERY_STATE'; END IF;
 IF v_received<>p_received_at THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='REQUEST_CONFLICT'; END IF;
 COMMIT;
 SELECT p_delivery_id AS delivery_id,v_lines AS lines_received,v_units AS units_received,'RECEIVED' AS status;
 LEAVE main;
 END IF;
 IF v_status<>'SCHEDULED' OR v_received IS NOT NULL THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_DELIVERY_STATE'; END IF;
 SELECT store_id,created_at INTO v_store,v_created FROM purchase_orders WHERE purchase_order_id=v_po FOR UPDATE;
 IF p_received_at<v_created THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_TIMESTAMP'; END IF;
 SELECT COUNT(*),COALESCE(SUM(quantity),0) INTO v_lines,v_units FROM delivery_lines WHERE delivery_id=p_delivery_id;
 IF v_lines=0 OR EXISTS(SELECT 1 FROM delivery_lines dl JOIN purchase_order_lines pol USING(purchase_order_line_id)
 WHERE dl.delivery_id=p_delivery_id AND (dl.quantity<=0 OR pol.purchase_order_id<>v_po)) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INVALID_DELIVERY_LINE'; END IF;
 IF EXISTS(SELECT 1 FROM delivery_lines dl JOIN purchase_order_lines pol USING(purchase_order_line_id)
 LEFT JOIN stock s ON s.product_id=pol.product_id AND s.store_id=v_store
 WHERE dl.delivery_id=p_delivery_id AND s.product_id IS NULL) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='STOCK_NOT_FOUND'; END IF;
 IF EXISTS(
 SELECT 1 FROM purchase_order_lines pol
 JOIN (SELECT purchase_order_line_id,SUM(quantity) AS batch_qty FROM delivery_lines
       WHERE delivery_id=p_delivery_id GROUP BY purchase_order_line_id) batch USING(purchase_order_line_id)
 LEFT JOIN (SELECT other.purchase_order_line_id,SUM(other.quantity) AS used_qty
            FROM delivery_lines other JOIN deliveries d USING(delivery_id)
            WHERE d.status='RECEIVED' AND d.received_at IS NOT NULL AND d.delivery_id<>p_delivery_id
            GROUP BY other.purchase_order_line_id) used USING(purchase_order_line_id)
 WHERE batch.batch_qty>CAST(pol.ordered_qty AS SIGNED)-pol.cancelled_qty-COALESCE(used.used_qty,0)) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='DELIVERY_LIMIT_EXCEEDED'; END IF;
 IF v_units>2147483647 OR v_lines>2147483647 OR EXISTS(
 SELECT 1 FROM stock s JOIN (
 SELECT pol.product_id,SUM(dl.quantity) AS batch_qty FROM delivery_lines dl
 JOIN purchase_order_lines pol USING(purchase_order_line_id)
 WHERE dl.delivery_id=p_delivery_id GROUP BY pol.product_id) batch USING(product_id)
 WHERE s.store_id=v_store AND CAST(s.on_hand AS SIGNED)+batch.batch_qty>2147483647) THEN
 SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='STOCK_OVERFLOW'; END IF;
 OPEN c_lines;
 receive_loop: LOOP
 FETCH c_lines INTO v_line,v_product,v_quantity;
 IF v_done THEN LEAVE receive_loop; END IF;
 UPDATE stock SET on_hand=on_hand+v_quantity WHERE store_id=v_store AND product_id=v_product;
 INSERT INTO stock_movements(store_id,product_id,quantity,occurred_at,delivery_line_id)
 VALUES(v_store,v_product,v_quantity,p_received_at,v_line);
 END LOOP;
 CLOSE c_lines;
 UPDATE deliveries SET status='RECEIVED',received_at=p_received_at,lines_received=v_lines,units_received=v_units
 WHERE delivery_id=p_delivery_id;
 COMMIT;
 SELECT p_delivery_id AS delivery_id,v_lines AS lines_received,v_units AS units_received,'RECEIVED' AS status;
END"""


def build_challenges(challenge):
    common = ["Use SQL SECURITY INVOKER. Submit a complete CREATE PROCEDURE and optional DROP; Run may also CALL it. Calls are top-level and serialized per workspace.",
              "Every validation error must SIGNAL SQLSTATE '45000' with the exact documented MESSAGE_TEXT, and return no success row. Unexpected errors must roll back and RESIGNAL. Preserve every unrelated business value."]
    return [challenge("BI-P01", "Transfer stock atomically", "inventory", "procedure", "Advanced",
        "Move stock between stores without transferring reserved units or leaving half a transfer behind.",
        "Combine stock availability, an audit ledger and stable request retries in one transaction.",
        ["Define transfer_stock(p_request_key VARCHAR(64), p_product_id BIGINT, p_source_store_id BIGINT, p_destination_store_id BIGINT, p_quantity INT, p_occurred_at DATETIME).",
         "NULL arguments, blank keys, non-positive IDs or quantity, and identical stores raise INVALID_ARGUMENT. Missing product, store or stock row at either end raises RECORD_NOT_FOUND; do not create stock rows.",
         "Available stock is source on_hand minus reserved. Insufficient availability raises INSUFFICIENT_STOCK. Destination on_hand above signed INT maximum 2147483647 raises STOCK_OVERFLOW; perform validation with wide arithmetic.",
         "Atomically subtract/add the quantity, preserve reservations, insert one transfers row and exactly two stock_movements linked by transfer_id with negative/positive quantity and the supplied timestamp. Do not impose a reporting cutoff on transfers.",
         "After argument validation, an existing request_key must return its original result for the same complete payload, even after later transfers change balances. Any changed payload raises REQUEST_CONFLICT before stock validation.",
         "Return exactly one row: transfer_id, quantity_transferred, status (COMPLETED). Example: CALL transfer_stock('practice-transfer',1,1,2,5,'2026-06-30 12:00:00');"] + common,
        ["A transfer consists of both balances and both ledger entries. Compare availability, rather than on_hand, before moving units.",
         "Have you considered a transaction, SELECT ... FOR UPDATE, a request-key lookup and an EXIT HANDLER for SQLEXCEPTION?",
         "The handler can use BEGIN ROLLBACK; RESIGNAL; END. Check request replay before current availability, so a successful retry cannot become an insufficient-stock error."],
        "DELIMITER $$\nCREATE PROCEDURE transfer_stock(IN p_request_key VARCHAR(64), IN p_product_id BIGINT, IN p_source_store_id BIGINT, IN p_destination_store_id BIGINT, IN p_quantity INT, IN p_occurred_at DATETIME)\nSQL SECURITY INVOKER\nBEGIN\n    -- Validate arguments, check replay, and transact balances plus audit rows.\n    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='NOT_IMPLEMENTED';\nEND$$\nDELIMITER ;",
        ["transfer_id", "quantity_transferred", "status"], ready=True, version="1.1.0", routine_name="transfer_stock", solution=TRANSFER_STOCK,
        explanation="Validate the request before looking up its original transfer, then replay that stored operation without consulting today's availability. Lock and validate both stock rows, update on_hand only, and link two opposite movements to the same transfer. A single rollback handler covers balances, transfer and ledger, including an unexpected insert failure after earlier writes. BIGINT local balances avoid overflow during validation. Jobs in one workspace are serialized; callers managing their own transactions and overlapping transfers are outside this exercise contract. For a concurrent service, lock stock rows in a consistent store order."),
        challenge("BI-P02", "Receive a delivery exactly once", "inventory", "procedure", "Advanced",
        "A retried warehouse receipt inflated stock. Repair a routine that misses state, line and transaction safeguards.",
        "Validate a multi-line state transition and persist a receipt response that remains stable on retry.",
        ["Define receive_delivery(p_delivery_id BIGINT, p_received_at DATETIME). NULL arguments or a non-positive ID raise INVALID_ARGUMENT; a missing delivery raises DELIVERY_NOT_FOUND.",
         "A new receipt requires status SCHEDULED and NULL received_at, otherwise INVALID_DELIVERY_STATE. Its timestamp must be at or after purchase_orders.created_at, otherwise INVALID_TIMESTAMP. Future timestamps are allowed.",
         "A batch must have at least one line, every quantity must be positive, and every purchase-order line must belong to the delivery's purchase order; violations raise INVALID_DELIVERY_LINE. Every product must have a stock row at that order's store, otherwise STOCK_NOT_FOUND.",
         "For each purchase-order line, sum all quantities in this batch, including duplicates. This sum may not exceed ordered_qty minus cancelled_qty minus quantities in other RECEIVED deliveries with non-NULL received_at; count these previous receipts regardless of their timestamps. Exceeding this allowance raises DELIVERY_LIMIT_EXCEEDED.",
         "Validate in this order: arguments, existence/state/retry, timestamp, line validity, stock existence, per-order-line allowance, overflow. If total units, line count, or any destination on_hand after the whole batch exceeds 2147483647, raise STOCK_OVERFLOW.",
         "Atomically add each line to destination on_hand, preserve reservations, insert one positive stock_movements row linked by delivery_line_id per line, and mark the delivery RECEIVED with received_at, lines_received (number of physical lines), units_received (sum of quantities). Preserve ordered and cancelled quantities.",
         "An already RECEIVED row needs non-NULL received_at and positive stored lines_received/units_received, otherwise INVALID_DELIVERY_STATE. The same timestamp returns those original stored totals; a different timestamp raises REQUEST_CONFLICT. Do not apply receipt stock or ledger entries again.",
         "Return exactly one row: delivery_id, lines_received, units_received, status (RECEIVED). Example: CALL receive_delivery(2,'2026-06-30 12:00:00'); The runnable starter is deliberately faulty: it changes stock without validation, ledger entries, transaction safety or retry protection. Repair all of these defects."] + common,
        ["Receiving the first line does not mean the batch succeeded. A repeat must return stored receipt totals without changing stock.",
         "Have you considered grouped validation for duplicate purchase-order lines, a cursor or set-based writes, and a transaction with an exception handler?",
         "A replay branch can begin: IF v_status = 'RECEIVED' THEN ... END IF. Compare the saved timestamp and return saved lines_received/units_received before applying any line."],
        "DELIMITER $$\nCREATE PROCEDURE receive_delivery(IN p_delivery_id BIGINT, IN p_received_at DATETIME)\nSQL SECURITY INVOKER\nBEGIN\n    -- Deliberately faulty: no validation, transaction, retry guard or ledger.\n    UPDATE stock s JOIN purchase_orders po ON po.store_id=s.store_id\n    JOIN deliveries d ON d.purchase_order_id=po.purchase_order_id\n    JOIN delivery_lines dl ON dl.delivery_id=d.delivery_id\n    JOIN purchase_order_lines pol ON pol.purchase_order_line_id=dl.purchase_order_line_id AND pol.product_id=s.product_id\n    SET s.on_hand=s.on_hand+dl.quantity WHERE d.delivery_id=p_delivery_id;\n    UPDATE deliveries SET status='RECEIVED',received_at=p_received_at WHERE delivery_id=p_delivery_id;\nEND$$\nDELIMITER ;",
        ["delivery_id", "lines_received", "units_received", "status"], ready=True, version="1.1.0", routine_name="receive_delivery", solution=RECEIVE_DELIVERY,
        explanation="A delivery is one state transition, so validate the entire batch and commit stock, linked movements and receipt metadata together. Group this batch by purchase-order line before comparing its allowance: checking duplicate lines separately admits over-delivery. Earlier actual receipts consume allowance even if their timestamps are after a reporting cutoff. Group by product too when checking destination INT capacity. Store physical line count and total units on the delivery, then return those saved totals on a same-timestamp retry after later receipts. A cursor is one solution; validated set-based stock updates and movement inserts are equally acceptable. The supplied starter has several documented defects and is not a nearly correct receipt algorithm.")]


def routine_probes(challenge_id, variant=0):
    b = 5000 + variant * 100
    at = "'2026-06-30 12:00:00'"
    if challenge_id == "BI-P01":
        def call(key, product=1, source=1, destination=2, quantity=5, stamp=at):
            return f"CALL transfer_stock({key},{product},{source},{destination},{quantity},{stamp})"
        cases = [(call("'initial-reservations'",source=2,destination=1,quantity=1), "Reservations exceeding on-hand prevent transfer"),
                 (call("'first'"), "Transfer preserves reserved units and balances"),
                 (call("'reverse'",source=2,destination=1,quantity=2), "A later transfer changes both balances"),
                 (call("'first'"), "Replay retains original response after later mutations")]
        for field, value in {"product": 2, "source": 2, "destination": 3, "quantity": 6, "stamp": "'2026-06-30 13:00:00'"}.items():
            cases.append((call("'first'", **{field:value}), f"Request conflict for changed {field}"))
        cases += [(call("'exact'",quantity=22), "Exactly all unreserved units can move"),
                  (call("'short'",quantity=1), "Reserved units cannot be transferred"),
                  (call("'negative-availability'",product=2,source=3,destination=1), "Missing source stock row"),
                  (call("'overflow'",product=b,source=2,destination=1,quantity=1), "Destination capacity uses wide arithmetic"),
                  (call("'missing-product'",product=999999), "Missing product"),
                  (call("'missing-store'",destination=999999), "Missing store"),
                  (call("'missing-stock'",destination=3), "Missing destination stock row"),
                  (call("'same'",destination=1), "Source and destination must differ")]
        for field in ("product","source","destination","quantity","stamp"):
            cases.append((call("'null'", **{field:"NULL"}), f"NULL {field} is invalid"))
        cases += [(call("NULL"),"NULL key"),(call("'   '"),"Blank key"),
                  (call("'zero'",quantity=0),"Zero quantity"),(call("'negative'",quantity=-1),"Negative quantity"),
                  (call("'insufficient'",product=b+1,quantity=1000),"Large unavailable quantity")]
        for field in ("product", "source", "destination"):
            for value in (0, -1):
                cases.append((call("'invalid-id'", **{field:value}), f"Non-positive {field} identifier ({value})"))
        cases += [(call("'after-cutoff'",product=b+1,quantity=1,stamp="'2026-07-02 12:00:00'"), "Transfers after the reporting cutoff remain valid"),
                  (call("'after-cutoff'",product=b+1,quantity=1,stamp="'2026-07-02 12:00:00'"), "Post-cutoff transfer replay is unchanged")]
        return cases
    if challenge_id == "BI-P02":
        def call(offset, stamp=at):
            return f"CALL receive_delivery({b+offset},{stamp})"
        return [(call(0,"'2026-05-01'"),"Order-creation timestamp is inclusive for a valid multi-line receipt"),
                (call(1),"Later receipt changes remaining allowance"),
                (call(0,"'2026-05-01'"),"Retry returns original physical-line and unit totals"),
                (call(0,"'2026-06-30 13:00:00'"),"Changed retry timestamp conflicts"),
                (call(2),"Duplicate lines jointly exceed remaining allowance"),
                (call(3),"Invalid later line leaves all earlier lines unchanged"),
                (call(4),"Line belongs to a different purchase order"),
                (call(5),"Destination stock row is required"),
                (call(6),"Cancelled delivery cannot be received"),
                (call(7),"Empty delivery is invalid"),(call(8),"Zero quantity is invalid"),
                (call(9),"Destination stock INT overflow is rejected"),
                (call(11),"Exact remaining allowance after cancellations and prior receipts"),
                (call(15),"Prior receipts after the reporting cutoff still consume allowance"),
                (call(12,"'2026-07-02'"),"An existing receipt returns saved original totals"),
                (call(13),"Incomplete received state cannot be replayed"),
                (call(14),"Receipt summary INT overflow is rejected"),
                (call(10,"'2026-04-30 23:59:59'"),"Timestamp before order creation"),
                ("CALL receive_delivery(999999,'2026-06-30')","Missing delivery"),
                ("CALL receive_delivery(NULL,'2026-06-30')","NULL delivery"),
                ("CALL receive_delivery(0,'2026-06-30')","Non-positive delivery"),
                (call(10,"NULL"),"NULL timestamp")]
    return []


def rollback_probes(challenge_id, variant=0):
    b = 5000 + variant * 100
    if challenge_id == "BI-P01":
        return [{"setup_sql": ["CREATE TRIGGER fail_transfer_movement BEFORE INSERT ON stock_movements FOR EACH ROW BEGIN IF NEW.transfer_id IS NOT NULL AND NEW.quantity>0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INJECTED_FAILURE'; END IF; END"],
                 "sql": f"CALL transfer_stock('injected',{b+1},1,2,1,'2026-06-30')", "label": "Unexpected database failure rolls back both balances and audit rows"}]
    if challenge_id == "BI-P02":
        return [{"setup_sql": [f"CREATE TRIGGER fail_receipt_movement BEFORE INSERT ON stock_movements FOR EACH ROW BEGIN IF NEW.delivery_line_id={b+14} THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='INJECTED_FAILURE'; END IF; END"],
                 "sql": f"CALL receive_delivery({b+10},'2026-06-30')", "label": "Unexpected database failure rolls back an earlier receipt line"}]
    return []
