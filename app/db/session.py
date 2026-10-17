from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# 1. The engine: a pool of open connections to Postgres. Created ONCE.
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# 2. A factory that produces sessions on demand.
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# 3. FastAPI dependency: one session per request, always closed afterwards.
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session