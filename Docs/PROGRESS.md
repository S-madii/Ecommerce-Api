# PROGRESS: commerce-api

Last updated: 2026-10-23. Source of truth for the plan: Roadmap v3 (outputs/Roadmap_v3_Styled.pdf). Update this file only when asked.

---

## Where we are

- **A1 Setup:** done.
- **A2 Schema design:** done. Reference is `Docs/schema.sql`.
- **A3 Database layer:** done per the user. All 9 tables exist in Postgres. Rollback round trip tested. Migrations `c9559598e2dd`, `eb0c06dad29b`, `e97321227f27`, `e4cdc75b1de7` applied, head is `e4cdc75b1de7`.
- **A4 JWT authentication:** in progress.
  - Done: `GET /users/{user_id}` uses `select(User)` and returns only `id`, `email`, `created_at`. The user confirmed 200 for an existing user and 404 for a missing one.
  - Not started: `BaseModel` schemas, signup, login, `/auth/me`.
  - Teaching doc written: `Docs/LEARN_jwt_auth.md`.
  - Decided: use `bcrypt` directly (no passlib), and `PyJWT` (no python-jose). requirements.txt updated.

## Files

- `app/main.py`: `/health`, `/health/db`, `/users/{user_id}`.
- `app/schemas/`: empty, only `__init__.py`.
- `app/routers/`: empty, only `__init__.py`.
- `app/models/`: user, category, product, cart (Cart and CartItem), order (Order, OrderItem, Payment).
- `app/core/config.py`: `SECRET_KEY` and `STRIPE_SECRET_KEY` are `SecretStr`. Add `ACCESS_TOKEN_EXPIRE_MINUTES` when JWT starts.
- `app/db/session.py`: `echo=True`, `expire_on_commit=False`, `get_db` dependency.
- `playground.py`: runs and cleans up after itself. The user says it's done. The category-first delete order is not in the file. Only mention this if the user raises it again.

## Open items

- A4: write schemas, signup, login, `/auth/me`, and include the router in `main.py`.
- Track B Stage 1 (freelance profiles): status unknown. Ask before assuming.
- Track C (reading and math habit): not started as far as we've discussed.

## Working agreements

- The user writes the code. Give hints, not full solutions.
- Batch tasks (8 to 12 per message). Teaching doc first for new tech.
- Explain every new file: purpose, why separate, what imports it.
- Replies in short bullets. Keep them lean because token budget is limited.
- The user confirms their own checks. Don't ask for output the user has said is fine.
- Session recap at the end of each session: what clicked, what's shaky, what's next.

## Docs in the repo

- `Docs/LEARN_sqlalchemy_alembic.md`: Part 6 guide.
- `Docs/FastApi_Async_Foundation.md`: the user's FastAPI and async doc, renamed from the one I wrote.
- `Docs/LEARN_jwt_auth.md`: Pydantic schemas, password hashing, JWT.
- `Docs/schema.sql`: database design reference.
- `Docs/Schema.jpg`: ERD image.

## Next step

Start the `BaseModel` schemas in `app/schemas/user.py`, then signup, login, and `/auth/me`.
