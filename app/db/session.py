from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# 1. The engine: a pool of open connections to Postgres. Created ONCE.
engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

# 2. A factory that produces sessions on demand.
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# 3. FastAPI dependency: one session per request, always closed afterwards.
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
        # session is automatically closed when the context manager exits
        # This is because the `async with` statement ensures that the `__aexit__` method is called,
        # which in turn calls the `close()` method on the session.
        # How? : The `async with` statement is a context manager that automatically calls the `__aenter__` method when entering the context and the `__aexit__` method when exiting the context. The `__aexit__` method is responsible for cleaning up the resources, in this case, closing the session.