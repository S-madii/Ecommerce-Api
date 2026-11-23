# PROGRESS: commerce-api

Last updated: 2026-11-19. Source of truth for the plan: Roadmap v4. Update this file only when asked.

---

## Where we are

- **A1 Setup:** done.
- **A2 Schema design:** done. Reference is `Docs/schema.sql`.
- **A3 Database layer:** done. All 9 tables exist in Postgres. Rollback round trip tested. Head revision is `e4cdc75b1de7`.
- **A4 JWT authentication:** done. Verified signup (201 & 409), login returning JWT token, and `/auth/me` with Bearer auth (200 & 401).
- **A5 Product & Category Catalog:** done 100%. Categories (create, read), Products (create with category validation and SKU conflict, read detail with `selectinload`, dynamic multi-filter with `q` autoescaping, price bounds, category, safe whitelist sorting with tiebreaker, and `ProductList` envelope with total count).
- **A6 Cart & Concurrency:** done 100%. Cart schemas, active cart session management, add/update/delete cart items, and POST /orders/checkout with deterministic deadlock-free row-level locking (`with_for_update`), atomic stock deduction, frozen price snapshotting in `order_items`, and cart status conversion.
- **A7 Stripe Payments (Test mode only):** done 100%. Service layer `PaymentService` (`create_payment_intent`, `verify_payment_intent`), `CheckoutResponse` with `client_secret`, checkout route integration with `flush()` to allocate `order.id`, and `POST /payments/webhook` with raw-bytes HMAC signature verification, idempotency handling, and order/payment status state machine transition to 'confirmed'/'succeeded'.
- **A8 Redis Caching & Celery:** next up.

## Files

- `app/main.py`: `/health`, `/health/db`, `/users/{user_id}`, mounts central `api_router`.
- `app/schemas/`: `user.py`, `category.py`, `product.py`, `cart.py`, `order.py`, `payment.py`.
- `app/routers/`: `auth.py`, `categories.py`, `products.py`, `cart.py`, `orders.py`, `payments.py`, with central aggregation in `app/routers/__init__.py`.
- `app/services/`: `cart.py` (CartService for active carts, item mutations), `order.py` (OrderService for checkout orchestration, decoupled locking, stock management), `payment.py` (PaymentService for Stripe PaymentIntent, webhook verification), `product.py` (ProductService for catalog search, filtering, pagination).
- `app/core/`: `config.py` (Settings with Stripe keys), `security.py` (create_access_token, get_current_user), `exceptions.py` (AppHTTPError, NotFoundError).
- `app/models/`: user, category, product, cart (Cart and CartItem), order (Order, OrderItem, Payment).
- `app/db/session.py`: `echo=True`, `expire_on_commit=False`, `get_db` dependency.
- `playground.py`: scratch script, done.

## Open items

- A8: Redis caching for popular catalog endpoints with invalidation, and one Celery background job (e.g. order confirmation email / abandoned cart cleanup).
- Track B Stage 1 (freelance profiles): lead declined. Stage 2 (payments) is now unlocked!
- Track C (reading and math habit): low intensity.

## Working agreements

- The user writes the code. Give hints, not full solutions.
- Batch tasks (8 to 12 per message). Teaching doc first for new tech.
- Explain every new file: purpose, why separate, what imports it.
- Replies in short bullets. Keep them lean because token budget is limited.
- The user confirms their own checks. Don't ask for output the user has said is fine.
- Session recap at the end of each session: what clicked, what's shaky, what's next.

## Docs in the repo

- `Docs/LEARN_sqlalchemy_alembic.md`: Part 6 guide.
- `Docs/FastApi_Async_Foundation.md`: FastAPI and async doc.
- `Docs/LEARN_jwt_auth.md`: Pydantic schemas, password hashing, JWT.
- `Docs/LEARN_catalog.md`: Catalog guide.
- `Docs/SKILL.md`: Comprehensive cheat sheet & reference for all concepts learned so far.
- `Docs/schema.sql`: database design reference.
- `Docs/Schema.jpg`: ERD image.

## Next step

Start Milestone A8: Redis caching and Celery background workers.
