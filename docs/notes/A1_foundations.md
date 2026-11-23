# Notes: Phase A1 — Project Foundations & Async Runtime

## Key Decisions
- **Async Runtime**: Python 3.12+ with native `async`/`await` powered by `uvicorn` and `asyncpg`.
- **Config Management**: Used `pydantic-settings` with `BaseSettings` reading from `.env`.
- **Secrets Protection**: Used `SecretStr` for `SECRET_KEY` and third-party API keys to prevent them from leaking into logs or tracebacks.
- **Session Lifecycle**: Configured `create_async_engine` with `echo=True` (in dev) and `expire_on_commit=False` so ORM instances remain usable in memory after committing.

## Common Traps & Lessons
- **Unwrapping SecretStr**: When passing secrets to libraries like `PyJWT` or `Stripe`, never pass the raw object. Always call `.get_secret_value()`.
- **`expire_on_commit=False`**: If left as default (`True`), accessing any object attribute after `await db.commit()` will trigger an unwanted synchronous query, throwing `MissingGreenlet`.
- **Dependency Generator**:
  ```python
  async def get_db() -> AsyncGenerator[AsyncSession, None]:
      async with SessionLocal() as session:
          yield session
  ```
  This guarantees database sessions are cleanly closed even if an exception occurs during the request.
