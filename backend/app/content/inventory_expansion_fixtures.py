"""Authored inventory reporting boundaries, separate from procedure fixtures."""


def augment_inventory(cursor, variant=0):
    shift = variant * 100
    ident = lambda n: 1000 + shift + n
    cursor.executemany("INSERT INTO suppliers VALUES(%s,%s)", [
        (ident(1), "Atlas supply"), (ident(2), "Quiet supplier"),
    ])
    cursor.executemany("INSERT INTO products VALUES(%s,%s,%s,%s)", [
        (ident(i), "Boundary stock" if i < 3 else f"Ledger item {i}", ident(1), pack)
        for i, pack in enumerate([6, 4, 6 + variant, 4, 5, 5, 3, 5, 2, 2, 2], 1)
    ])
    stocks = [
        (1, 2, 8, 10, 25),       # Negative availability; no inbound.
        (2, 5, 0, 10, 31),       # Exactly at trigger after inbound.
        (3, 0, 0, 10, 25),       # Pack rounding and multiple receipts.
        (4, 1, 0, 20, 31),       # Floor each PO line before summing.
        (5, 0, 0, 10, 30),
        (6, 5, 0, 20, 30),       # A receipt at cutoff remains open at cutoff.
        (7, 8, 0, 10, 20),
        (8, 2, 0, 10, 20),
        (9, 0, 0, 10, 20),
        (10, 0, 0, 10, 20),      # Negative opening and no June movements.
        (11, 3, 0, 10, 20),      # Stock with no ledger entries at all.
    ]
    cursor.executemany("INSERT INTO stock VALUES(%s,%s,%s,%s,%s,%s)", [
        (3, ident(i), hand, reserved, point, target)
        for i, hand, reserved, point, target in stocks
    ])
    cursor.executemany("INSERT INTO purchase_orders VALUES(%s,%s,%s,%s)", [
        (ident(1), ident(1), 3, "2026-03-01"),
        (ident(2), ident(2), 3, "2026-03-01"),
        (ident(3), ident(1), 3, "2026-07-01"),
    ])
    cursor.executemany("INSERT INTO purchase_order_lines VALUES(%s,%s,%s,%s,%s)", [
        (ident(1), ident(1), ident(2), 9, 4),
        (ident(2), ident(1), ident(3), 20, 3),
        (ident(3), ident(1), ident(4), 4, 0),
        (ident(4), ident(1), ident(4), 5, 0),
        (ident(5), ident(1), ident(6), 20, 0),
        (ident(6), ident(3), ident(5), 100, 0),
    ])
    cursor.executemany("INSERT INTO deliveries VALUES(%s,%s,%s,%s,%s,%s,%s)", [
        (ident(1), ident(1), "2026-04-01", "2026-04-01", "RECEIVED", 3, 11),
        (ident(2), ident(1), "2026-05-10", "2026-05-10" if variant == 1 else "2026-05-11", "RECEIVED", 2, 11),
        (ident(3), ident(1), "2026-06-30 23:59:59", "2026-07-01", "RECEIVED", 1, 10),
        (ident(4), ident(1), "2026-06-30" if variant == 2 else "2026-07-01", None, "SCHEDULED", None, None),
        (ident(5), ident(2), "2026-06-01", None, "CANCELLED", None, None),
        (ident(6), ident(1), "2026-03-31 23:59:59", None, "SCHEDULED", None, None),
    ])
    cursor.executemany("INSERT INTO delivery_lines VALUES(%s,%s,%s,%s)", [
        (ident(1), ident(1), ident(2), 6),
        (ident(2), ident(1), ident(3), 3),
        (ident(3), ident(1), ident(4), 2),
        (ident(4), ident(2), ident(2), 8),
        (ident(5), ident(2), ident(3), 3),
        (ident(6), ident(3), ident(5), 10),
    ])
    # Explicit IDs make the two same-time sequences stable in every fixture.
    movements = [
        (1, 1, 2, "2026-05-31 23:59:59"),
        (2, 2, 5, "2026-05-01"),
        (3, 3, 4 + variant, "2026-05-01"),
        (4, 3, -2, "2026-06-01"),
        (5, 4, 1, "2026-05-01"),
        (6, 5, -3, "2026-05-01"),
        (7, 5, 3, "2026-06-10"),
        (8, 6, 5, "2026-05-01"),
        (9, 6, -10, "2026-07-01"),
        (10, 7, 10, "2026-05-01"),
        (11, 7, -5, "2026-06-01"),
        (12, 7, 3, "2026-06-30 23:59:59"),
        (13, 8, -2, "2026-05-01"),
        (14, 8, 4, "2026-06-10"),
        (15, 9, 6, "2026-06-10"),
        (16, 9, -6, "2026-06-10"),
        (17, 10, -4, "2026-05-01"),
    ]
    cursor.executemany("INSERT INTO stock_movements(movement_id,store_id,product_id,quantity,occurred_at) VALUES(%s,%s,%s,%s,%s)", [
        (ident(i), 3, ident(product), qty, at) for i, product, qty, at in movements
    ])
