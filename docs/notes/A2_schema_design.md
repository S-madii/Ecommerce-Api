# Notes: Phase A2 — Relational Schema Design & Constraints

## Key Decisions
- **9 Core Tables**: `users`, `categories`, `products`, `carts`, `cart_items`, `orders`, `order_items`, `payments`.
- **Primary Keys**: Used `BigInteger` with Postgres `Identity(always=True)` for 64-bit scale.
- **Currency & Money**: Always stored as `Numeric(12, 2)` mapped to Python `Decimal`. **Never use `float`** due to IEEE 754 binary representation rounding bugs.

## Specialized Indexes & Constraints
1. **Case-Insensitive Email Index**:
   ```sql
   CREATE UNIQUE INDEX uq_users_email_lower ON users (lower(email));
   ```
   Ensures `user@example.com` and `USER@EXAMPLE.COM` cannot duplicate. Always query with `func.lower(User.email) == email.lower()`.
2. **Partial Unique Index on Active Carts**:
   ```sql
   CREATE UNIQUE INDEX uq_carts_one_active_per_user ON carts (user_id) WHERE status = 'active';
   ```
   Guarantees a user has at most **1 active cart**, while allowing unlimited historical converted or abandoned carts.
3. **Price & Quantity CheckConstraints**:
   ```sql
   CHECK (stock >= 0)
   CHECK (price >= 0)
   CHECK (quantity > 0)
   ```
   Enforced at the storage layer so bugs in application code cannot write negative inventory.

## Foreign Key Cascades:
- `carts -> cart_items`: `CASCADE` (deleting a cart safely wipes its transient items).
- `orders -> order_items`: `RESTRICT` (legal accounting records must never be accidentally deleted).
- `products -> order_items`: `SET NULL` (if a product is deleted from the catalog, the historical receipt remains intact).
