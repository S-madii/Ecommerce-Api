# Notes: Phase A4 — Stateless JWT Authentication & Security

## Key Decisions
- **Direct `bcrypt`**: Avoided `passlib` because it is unmaintained and incompatible with modern bcrypt versions.
- **Stateless Tokens**: Used `PyJWT` (`import jwt`) with HMAC-SHA256 (`HS256`).
- **Token Claims**: Kept minimal: `sub` (user ID as string) and `exp` (UTC timestamp). Never store passwords or sensitive data in a JWT (JWT is signed, not encrypted!).

## Common Traps & Lessons
- **Timing Attack Mitigation**:
  If a user doesn't exist during login, query execution is faster than if the user exists and bcrypt runs. Attackers can time responses to enumerate valid emails.
  - **Fix**: Run `bcrypt.checkpw(password.encode(), DUMMY_HASH)` when a user is not found, so both branches take the exact same time.
- **Race Condition on Signup**:
  Don't do `SELECT` before `INSERT`. Two requests hitting at once will both pass the check.
  - **Fix**: Directly `INSERT`, let Postgres enforce the unique index, catch `sqlalchemy.exc.IntegrityError`, call `await db.rollback()`, and return HTTP 409 Conflict.
- **Always Rollback Poisoned Sessions**:
  In SQLAlchemy, if an `IntegrityError` occurs and you don't call `await db.rollback()`, the session remains poisoned and will crash all subsequent queries.
- **Dependency Guard (`get_current_user`)**:
  Used `fastapi.security.HTTPBearer` to extract the `Authorization: Bearer <token>` header and validate the user on every protected route.
