# PROGRESS: commerce-api

Last updated: 2026-11-05. Source of truth for the plan: Roadmap v4. Update this file only when asked.

---

## Where we are

- **A1 Setup:** done.
- **A2 Schema design:** done. Reference is `Docs/schema.sql`.
- **A3 Database layer:** done. All 9 tables exist in Postgres. Rollback round trip tested. Head revision is `e4cdc75b1de7`.
- **A4 JWT authentication:** done. Verified signup (201 & 409), login returning JWT token, and `/auth/me` with Bearer auth (200 & 401).
- **A5 Product & Category Catalog:** done. Schemas, `categories.py` (POST, GET), `products.py` (POST, GET with filters/pagination, GET /{id}), eager loading via `selectinload` verified.
- **A6 Cart & Concurrency:** in progress.

## Files

- `app/main.py`: `/health`, `/health/db`, `/users/{user_id}`, includes `auth_router`, `category_router`, `product_router`.
- `app/schemas/`: `user.py`, `category.py`, `product.py`.
- `app/routers/`: `auth.py`, `categories.py`, `products.py`.
- `app/core/`: `config.py` (Settings), `security.py` (create_access_token, get_current_user), `exceptions.py` (AppHTTPError, NotFoundError).
- `app/models/`: user, category, product, cart (Cart and CartItem), order (Order, OrderItem, Payment).
- `app/db/session.py`: `echo=True`, `expire_on_commit=False`, `get_db` dependency.
- `playground.py`: scratch script, done.

## Open items

- A6: Cart management (add/update/delete items) and checkout with concurrency lock (`with_for_update`).
- Track B Stage 1 (freelance profiles): lead declined, in progress.
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
- `Docs/schema.sql`: database design reference.
- `Docs/Schema.jpg`: ERD image.

## Next step

Create `app/schemas/cart.py`, then build `app/routers/cart.py` (GET /cart, POST /cart/items).
