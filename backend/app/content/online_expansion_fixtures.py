"""Extra reporting relationships without changing the original routine probes."""


def augment_online(cursor, variant=0):
    shift = variant * 100
    cursor.executemany("INSERT INTO products VALUES(%s,%s,%s)", [
        (6, 1, "Precision tool" if not variant else f"Precision tool variant {variant}"),
        (7, 1, "Budget tool"), (8, 2, "Sample pack"), (9, 1, "Reclassified item")])
    cursor.executemany("INSERT INTO calendar_months VALUES(%s)", [("2025-12-01",), ("2026-07-01",)])
    order = 1000 + shift
    cursor.execute("INSERT INTO orders VALUES(%s,%s,'COMPLETED',%s)",
                   (order, 3+shift, f"2026-06-{15+variant:02d} 12:00:00"))
    # Product 9 is now catalogued in category 1, but was sold in category 2.
    amounts = [50+17*variant, 650+17*variant, 20+11*variant,
               520+11*variant, 200, 120, 50, 90]
    products = [1, 5, 2, 6, 7, 8, 4, 9]
    categories = [1, 1, 1, 1, 1, 2, 3, 2]
    cursor.executemany("INSERT INTO order_items VALUES(%s,%s,%s,%s,%s,%s)", [
        (1000+shift+i, order, product, category, 1, amount)
        for i, (product, category, amount) in enumerate(zip(products, categories, amounts))])
    cursor.execute("INSERT INTO payments(payment_id,order_id,amount,status,captured_at) VALUES(%s,%s,%s,'SUCCESS',%s)",
                   (1000+shift, order, sum(amounts), f"2026-06-{15+variant:02d} 12:00:00"))
    refunds = [
        (1000+shift, f"trend-partial-{variant}", 1004+shift, 50, "POSTED", "2026-06-20", 150),
        (1001+shift, f"trend-pending-{variant}", 1004+shift, 25, "PENDING", "2026-06-21", None),
        (1002+shift, f"trend-cutoff-{variant}", 1004+shift, 30, "POSTED", "2026-07-01", 120),
        (1003+shift, f"trend-full-{variant}", 1005+shift, 120, "POSTED", "2026-06-20", 0),
    ]
    cursor.executemany("INSERT INTO refunds VALUES(%s,%s,%s,%s,%s,%s,%s,%s)", [
        (id, key, item, 1000+shift, amount, status, at, remaining)
        for id, key, item, amount, status, at, remaining in refunds])
    cursor.execute("UPDATE payments SET refunded_amount=200 WHERE payment_id=%s", (1000+shift,))
