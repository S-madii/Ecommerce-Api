---
tags:
  - notes
  - architecture
  - async
  - fastapi
---

# ⚙️ Notes: Phase A1 — Project Foundations & Async Runtime

> [!abstract] Overview
> Setting up a modern, asynchronous FastAPI backend with PostgreSQL connectivity via `asyncpg`, configuration validation through `pydantic-settings`, and session lifecycles.

---

## 🛠️ Key Architectural Decisions

### 1. The Async Runtime
- **Stack**: Python 3.12+ with native `async`/`await` powered by `uvicorn` (ASGI server) and `asyncpg`.
- **Why**: Async I/O allows a single worker thread to handle thousands of concurrent idle network connections without blocking the operating system thread during database I/O.

### 2. Configuration Management
- Used `pydantic-settings` with `BaseSettings` reading from `.env`.
- **Secrets Protection**: Used `SecretStr` for sensitive credentials (`SECRET_KEY`, `STRIPE_SECRET_KEY`) to prevent them from accidentally leaking into console logs, terminal output, or traceback logs.

### 3. Session Lifecycle & Engine
- Configured `create_async_engine` with:
  - `echo=True` (in local development for SQL statement visibility).
  - `expire_on_commit=False`: Prevents SQLAlchemy from expiring in-memory attributes when `await db.commit()` is called.

---

## ⚠️ Common Traps & Lessons Learned

> [!danger] Trap 1: Passing `SecretStr` directly to libraries
> Passing `settings.SECRET_KEY` directly to `PyJWT` or `Stripe` passes an instance of `SecretStr`, not a `str`.
> **Solution**: Always unwrap at the point of use with `.get_secret_value()`.

> [!warning] Trap 2: The `expire_on_commit` Greenlet Trap
> If `expire_on_commit=True` (the default), accessing an object attribute after committing triggers an implicit synchronous lazy-load, throwing a `MissingGreenlet` error in async mode.
> **Solution**: Always set `expire_on_commit=False` on the async sessionmaker.

> [!tip] Best Practice: Safe Scoped Dependency Injection
> ```python
> async def get_db() -> AsyncGenerator[AsyncSession, None]:
>     async with SessionLocal() as session:
>         yield session
> ```
> Guarantees connections are safely returned to the connection pool even if an unhandled route exception is thrown.

---

## 🔗 Related Notes & Deep Dives
- 🗺️ [[roadmap|Project Roadmap]]
- ⚡ [[learning/FastApi_Async_Foundation|Deep Dive: FastAPI & Async Event Loops]]
- ➡️ Next Milestone: [[notes/A2_schema_design|A2: Schema Design]]
