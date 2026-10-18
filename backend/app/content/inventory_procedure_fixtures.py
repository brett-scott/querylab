"""Deterministic receipt/transfer edge cases, also included in downloadable data."""


def augment_inventory_procedures(cursor, variant=0):
    b = 5000 + variant * 100
    cursor.executemany("INSERT INTO products VALUES(%s,%s,1,1)",
                       [(b+i, f"Receipt fixture {i}") for i in range(7)])
    stocks = [(1,b,2147483647,0,1,10),(2,b,20,0,1,10),
              (1,b+1,20+variant,2,5,30),(2,b+1,10,1,5,30),
              (1,b+2,10,2,5,30),(1,b+3,20,3,5,30),
              (2,b+4,10,0,5,20),(1,b+5,0,0,5,20),(1,b+6,0,0,5,20)]
    cursor.executemany("INSERT INTO stock VALUES(%s,%s,%s,%s,%s,%s)", stocks)
    cursor.executemany("INSERT INTO purchase_orders VALUES(%s,1,%s,'2026-05-01')", [(b,1),(b+1,2)])
    po_lines = [(b,b,b+2,100,10),(b+1,b,b+3,100,0),(b+2,b+1,b+4,10,0),
                (b+3,b,b+4,10,0),(b+4,b,b,10,0),(b+5,b,b+5,6,1),
                (b+6,b,b+6,2147483647,0)]
    cursor.executemany("INSERT INTO purchase_order_lines VALUES(%s,%s,%s,%s,%s)", po_lines)
    deliveries = [(b+i,b,'2026-06-15',None,'SCHEDULED',None,None) for i in range(16)]
    deliveries[6] = (b+6,b,'2026-06-15',None,'CANCELLED',None,None)
    deliveries[12] = (b+12,b,'2026-06-01','2026-07-02','RECEIVED',1,2)
    deliveries[13] = (b+13,b,'2026-06-15',None,'RECEIVED',None,None)
    cursor.executemany("INSERT INTO deliveries VALUES(%s,%s,%s,%s,%s,%s,%s)", deliveries)
    # Duplicate purchase-order lines in a batch require cumulative validation.
    lines = [(0,0,0,10+variant),(1,0,1,20),(2,0,0,5),
             (3,1,0,5),(4,2,0,40),(5,2,0,40),
             (6,3,0,1),(7,3,1,-1),(8,4,2,1),(9,5,3,1),
             (10,6,0,1),(11,8,0,0),(12,9,4,1),
             (13,10,0,1),(14,10,1,1),(15,11,5,3),(16,12,5,2),
             (17,14,6,2147483647),(18,14,1,1),(19,15,5,1)]
    cursor.executemany("INSERT INTO delivery_lines VALUES(%s,%s,%s,%s)",
                       [(b+i,b+d,b+p,q) for i,d,p,q in lines])
    cursor.executemany("INSERT INTO stock_movements(store_id,product_id,quantity,occurred_at) VALUES(%s,%s,%s,'2026-05-01')",
                       [(s,p,q) for s,p,q,_,_,_ in stocks])
