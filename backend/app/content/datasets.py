"""Versioned synthetic teaching fixtures. Hidden variants stay server-side."""
from .online_expansion_fixtures import augment_online
from .inventory_expansion_fixtures import augment_inventory
from .inventory_procedure_fixtures import augment_inventory_procedures
ONLINE_DDL = [
"CREATE TABLE customers(customer_id BIGINT PRIMARY KEY, customer_name VARCHAR(100) NOT NULL)",
"CREATE TABLE categories(category_id BIGINT PRIMARY KEY, category_name VARCHAR(100) NOT NULL)",
"CREATE TABLE products(product_id BIGINT PRIMARY KEY, category_id BIGINT NOT NULL, product_name VARCHAR(100) NOT NULL, FOREIGN KEY(category_id) REFERENCES categories(category_id))",
"CREATE TABLE orders(order_id BIGINT PRIMARY KEY, customer_id BIGINT NOT NULL, status VARCHAR(20) NOT NULL, completed_at DATETIME NULL, FOREIGN KEY(customer_id) REFERENCES customers(customer_id))",
"CREATE TABLE order_items(order_item_id BIGINT PRIMARY KEY, order_id BIGINT NOT NULL, product_id BIGINT NOT NULL, category_id BIGINT NOT NULL, quantity INT NOT NULL, unit_price DECIMAL(12,2) NOT NULL, FOREIGN KEY(order_id) REFERENCES orders(order_id), FOREIGN KEY(product_id) REFERENCES products(product_id), FOREIGN KEY(category_id) REFERENCES categories(category_id))",
"CREATE TABLE payments(payment_id BIGINT PRIMARY KEY, order_id BIGINT NOT NULL, amount DECIMAL(12,2) NOT NULL, status VARCHAR(20) NOT NULL, captured_at DATETIME NULL, refunded_amount DECIMAL(12,2) NOT NULL DEFAULT 0, FOREIGN KEY(order_id) REFERENCES orders(order_id))",
"CREATE TABLE refunds(refund_id BIGINT PRIMARY KEY AUTO_INCREMENT, request_key VARCHAR(64) NOT NULL UNIQUE, order_item_id BIGINT NOT NULL, payment_id BIGINT NOT NULL, amount DECIMAL(12,2) NOT NULL, status VARCHAR(20) NOT NULL, refunded_at DATETIME NOT NULL, item_remaining_refundable DECIMAL(12,2) NULL, FOREIGN KEY(order_item_id) REFERENCES order_items(order_item_id), FOREIGN KEY(payment_id) REFERENCES payments(payment_id))",
"CREATE TABLE calendar_months(month_start DATE PRIMARY KEY)",
]

INVENTORY_DDL = [
"CREATE TABLE stores(store_id BIGINT PRIMARY KEY, store_name VARCHAR(100) NOT NULL)",
"CREATE TABLE suppliers(supplier_id BIGINT PRIMARY KEY, supplier_name VARCHAR(100) NOT NULL)",
"CREATE TABLE products(product_id BIGINT PRIMARY KEY, product_name VARCHAR(100) NOT NULL, supplier_id BIGINT NOT NULL, pack_size INT NOT NULL, FOREIGN KEY(supplier_id) REFERENCES suppliers(supplier_id))",
"CREATE TABLE stock(store_id BIGINT, product_id BIGINT, on_hand INT NOT NULL, reserved INT NOT NULL, reorder_point INT NOT NULL, target_qty INT NOT NULL, PRIMARY KEY(store_id,product_id), FOREIGN KEY(store_id) REFERENCES stores(store_id), FOREIGN KEY(product_id) REFERENCES products(product_id))",
"CREATE TABLE purchase_orders(purchase_order_id BIGINT PRIMARY KEY, supplier_id BIGINT NOT NULL, store_id BIGINT NOT NULL, created_at DATETIME NOT NULL, FOREIGN KEY(supplier_id) REFERENCES suppliers(supplier_id), FOREIGN KEY(store_id) REFERENCES stores(store_id))",
"CREATE TABLE purchase_order_lines(purchase_order_line_id BIGINT PRIMARY KEY, purchase_order_id BIGINT NOT NULL, product_id BIGINT NOT NULL, ordered_qty INT NOT NULL, cancelled_qty INT NOT NULL, FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders(purchase_order_id), FOREIGN KEY(product_id) REFERENCES products(product_id))",
"CREATE TABLE deliveries(delivery_id BIGINT PRIMARY KEY, purchase_order_id BIGINT NOT NULL, promised_at DATETIME NOT NULL, received_at DATETIME NULL, status VARCHAR(20) NOT NULL, lines_received INT NULL, units_received INT NULL, FOREIGN KEY(purchase_order_id) REFERENCES purchase_orders(purchase_order_id))",
"CREATE TABLE delivery_lines(delivery_line_id BIGINT PRIMARY KEY, delivery_id BIGINT NOT NULL, purchase_order_line_id BIGINT NOT NULL, quantity INT NOT NULL, FOREIGN KEY(delivery_id) REFERENCES deliveries(delivery_id), FOREIGN KEY(purchase_order_line_id) REFERENCES purchase_order_lines(purchase_order_line_id))",
"CREATE TABLE transfers(transfer_id BIGINT PRIMARY KEY AUTO_INCREMENT, request_key VARCHAR(64) NOT NULL UNIQUE, product_id BIGINT NOT NULL, source_store_id BIGINT NOT NULL, destination_store_id BIGINT NOT NULL, quantity INT NOT NULL, occurred_at DATETIME NOT NULL)",
"CREATE TABLE stock_movements(movement_id BIGINT PRIMARY KEY AUTO_INCREMENT, store_id BIGINT NOT NULL, product_id BIGINT NOT NULL, quantity INT NOT NULL, occurred_at DATETIME NOT NULL, transfer_id BIGINT NULL, delivery_line_id BIGINT NULL, FOREIGN KEY(store_id) REFERENCES stores(store_id), FOREIGN KEY(product_id) REFERENCES products(product_id), FOREIGN KEY(transfer_id) REFERENCES transfers(transfer_id), FOREIGN KEY(delivery_line_id) REFERENCES delivery_lines(delivery_line_id))",
]


def seed_online(cursor, variant=0):
    # Variant values intentionally change identifiers/names/amounts while keeping
    # the public business contract stable. Boundary records are always present.
    shift = variant * 100
    names = ["Maya Chen", "Sam Rivera", "Alex Kim", "Alex Kim", "Noor Ali", "Evan Park", "Jules Reed", "Pat Lane"]
    cursor.executemany("INSERT INTO customers VALUES(%s,%s)", [(i+shift, n if not variant else n+f" {variant}") for i,n in enumerate(names,1)])
    cursor.execute("INSERT INTO categories VALUES (1,'Equipment'),(2,'Supplies'),(3,'Accessories')")
    cursor.execute("INSERT INTO products VALUES (1,1,'Workshop kit'),(2,1,'Precision tool'),(3,2,'Paper pack'),(4,3,'Carry case'),(5,1,'Workshop kit')")
    orders = [
        (1,1,'COMPLETED','2026-01-10 10:00:00'),(2,1,'COMPLETED','2026-02-20 10:00:00'),
        (3,2,'COMPLETED','2026-03-01 09:00:00'),(4,3,'COMPLETED','2026-06-05 12:00:00'),
        (5,4,'COMPLETED','2026-04-02 00:00:00'), # exactly 90-day boundary
        (6,5,'CANCELLED','2026-06-01 10:00:00'),(7,5,'COMPLETED','2026-03-10 10:00:00'),
        (8,6,'COMPLETED','2026-07-01 00:00:00'), # excluded cutoff
        (9,6,'COMPLETED','2026-02-10 10:00:00'),(10,7,'COMPLETED','2026-04-01 23:59:59'),
        (11,3,'COMPLETED','2026-02-01 10:00:00'),(12,2,'PENDING',None),
        (13,1,'COMPLETED','2026-07-02 00:00:00')]
    cursor.executemany("INSERT INTO orders VALUES(%s,%s,%s,%s)", [(i+shift,c+shift,s,t) for i,c,s,t in orders])
    amounts = [600+variant*25,400,500,100,600,1000,800,900,600,500,800,1000,100]
    items = []
    for index, amount in enumerate(amounts,1):
        p = 1 if index%2 else 2
        items.append((index+shift,index+shift,p,1,1,amount))
    # Multiple items and payments make wide-join aggregation incorrect.
    items += [(20+shift,1+shift,3,2,2,75),(21+shift,4+shift,4,3,2,50)]
    cursor.executemany("INSERT INTO order_items VALUES(%s,%s,%s,%s,%s,%s)",items)
    payments = [(i+shift,i+shift,a+200,'SUCCESS',t or '2026-06-01 00:00:00') for (i,c,s,t),a in zip(orders,amounts)]
    payments += [(20+shift,1+shift,200,'SUCCESS','2026-01-10 10:00:00'),(21+shift,1+shift,100,'FAILED','2026-01-10 10:00:00')]
    cursor.executemany("INSERT INTO payments(payment_id,order_id,amount,status,captured_at) VALUES(%s,%s,%s,%s,%s)",payments)
    refunds = [
        (1,'seed-a',1,1,100,'POSTED','2026-01-20 10:00:00',500+variant*25),
        (2,'seed-b',1,1,50,'POSTED','2026-02-01 10:00:00',450+variant*25),
        (3,'seed-c',4,4,100,'POSTED','2026-06-10 10:00:00',0),
        (4,'seed-d',7,7,400,'POSTED','2026-03-20 10:00:00',400),
        (5,'seed-e',9,9,100,'POSTED','2026-07-01 00:00:00',500),
        (6,'seed-f',2,2,80,'PENDING','2026-03-01 10:00:00',None),
        (7,'seed-g',20,20,25,'POSTED','2026-02-10 10:00:00',125),
        (8,'seed-h',21,4,100,'POSTED','2026-06-10 10:00:00',0)]
    cursor.executemany("INSERT INTO refunds VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", [(i+shift,k+str(variant),item+shift,pay+shift,a,s,t,r) for i,k,item,pay,a,s,t,r in refunds])
    cursor.execute("UPDATE payments p SET refunded_amount=(SELECT COALESCE(SUM(r.amount),0) FROM refunds r WHERE r.payment_id=p.payment_id AND r.status='POSTED')")
    cursor.executemany("INSERT INTO calendar_months VALUES(%s)",[(f'2026-{m:02d}-01',) for m in range(1,7)])
    augment_online(cursor, variant)


def seed_inventory(cursor, variant=0):
    cursor.execute("INSERT INTO stores VALUES(1,'North warehouse'),(2,'City store'),(3,'West depot')")
    cursor.execute("INSERT INTO suppliers VALUES(1,'Atlas supply'),(2,'Bluebird goods'),(3,'Cedar trade')")
    cursor.execute("INSERT INTO products VALUES(1,'Workshop kit',1,6),(2,'Precision tool',1,4),(3,'Paper pack',2,10),(4,'Safety gloves',2,5)")
    cursor.execute("INSERT INTO stock VALUES(1,1,30,5,20,60),(2,1,5,8,10,30),(1,2,8,2,10,25),(2,2,10,0,10,30),(1,3,0,0,10,30),(2,3,20,0,10,30),(1,4,50,0,15,40)")
    cursor.execute("INSERT INTO purchase_orders VALUES(1,1,1,'2026-04-01'),(2,2,1,'2026-05-01'),(3,1,2,'2026-06-01')")
    cursor.execute("INSERT INTO purchase_order_lines VALUES(1,1,1,40,4),(2,1,2,20,0),(3,2,3,40,0),(4,3,1,20,0)")
    cursor.execute("INSERT INTO deliveries VALUES(1,1,'2026-04-15','2026-04-15','RECEIVED',2,16),(2,1,'2026-06-10',NULL,'SCHEDULED',NULL,NULL),(3,2,'2026-06-20','2026-07-02','RECEIVED',1,10),(4,2,'2026-06-25',NULL,'CANCELLED',NULL,NULL),(5,3,'2026-06-28','2026-06-29','RECEIVED',1,6)")
    cursor.execute("INSERT INTO delivery_lines VALUES(1,1,1,10),(2,1,2,6),(3,2,1,12),(4,2,2,8),(5,3,3,10),(6,4,3,10),(7,5,4,6)")
    cursor.execute("INSERT INTO stock_movements(store_id,product_id,quantity,occurred_at) SELECT store_id,product_id,on_hand,'2026-05-01' FROM stock")
    cursor.execute("INSERT INTO stock_movements(store_id,product_id,quantity,occurred_at) VALUES(1,1,-35,'2026-06-05'),(1,1,35,'2026-06-05'),(1,2,3,'2026-06-10')")
    if variant:
        cursor.execute("UPDATE stock SET reserved=reserved+%s WHERE store_id=1 AND product_id=2",(variant,))
        cursor.execute("UPDATE products SET pack_size=pack_size+%s WHERE product_id=2",(variant,))
    augment_inventory(cursor, variant)
    augment_inventory_procedures(cursor, variant)


DATASETS = {
    "online-store": {"name": "Online store", "ddl": ONLINE_DDL, "seed": seed_online},
    "inventory": {"name": "Business / inventory", "ddl": INVENTORY_DDL, "seed": seed_inventory},
}
