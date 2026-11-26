from collections.abc import AsyncGenerator

import httpx
import pytest_asyncio
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401 - ensure all models are registered on Base.metadata
from app.core.config import settings
from app.core.redis import redis_client
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# 1. Point test engine at the isolated 'commerce_test' database
# NullPool prevents connection loop-affinity errors across async test functions
TEST_DATABASE_URL = str(make_url(settings.DATABASE_URL).set(database="commerce_test"))

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool,
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db() -> AsyncGenerator[None, None]:
    """Creates tables in commerce_test and wipes rows + Redis cache before each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            text(
                "TRUNCATE TABLE payments, order_items, orders, cart_items, carts, "
                "products, categories, users RESTART IDENTITY CASCADE"
            )
        )
    try:
        await redis_client.flushdb()
    except RedisError:
        pass

    yield

    try:
        await redis_client.flushdb()
        await redis_client.aclose()
    except RedisError:
        pass


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Direct database session fixture for seeding or inspecting test state."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """In-memory async HTTP client wired to use the isolated test database."""
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
