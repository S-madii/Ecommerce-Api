# Notes: Phase A6 — Cart Mechanics & Pessimistic Concurrency (Checkout)

## Key Decisions
- **Get-or-Create Active Cart**: Active carts are automatically initialized if missing. When an order completes, the cart is transitioned to `status = 'converted'`, allowing subsequent requests to cleanly generate a new active cart.
- **Multi-Tenancy Scoping**: Every cart item update or deletion must be scoped: `CartItem.id == item_id` **and** `CartItem.cart_id == cart.id`. Never query by ID alone.
- **Pessimistic Row-Level Locking (`SELECT ... FOR UPDATE`)**:
  ```python
  stmt = (
      select(Product)
      .where(Product.id.in_(product_ids))
      .order_by(Product.id.asc())
      .with_for_update()
  )
  ```

## Common Traps & Lessons
- **Race Condition / Overselling**:
  Without row locks, two checkouts on `stock = 1` both read `1`, both deduct, and leave inventory at `-1`. `with_for_update()` forces concurrent requests to wait until the lock holder commits or rolls back.
- **Deadlock Elimination**:
  If User A locks Product 1 then waits for Product 2, while User B locks Product 2 then waits for Product 1, Postgres aborts with a deadlock.
  - **Rule**: Always sort product IDs numerically (`sorted(product_ids)`) before locking. Every transaction locks rows in the exact same sequence.
- **Rollback on Insufficient Stock**:
  If stock check fails halfway through, calling `await db.rollback()` is mandatory to immediately release row locks so other shoppers aren't blocked.
- **Price Snapshotting (`OrderItem`)**:
  Store prices change over time, but legal receipts and invoices must never mutate. On checkout, freeze `unit_price`, `sku`, and `product_name` directly into `order_items`.
