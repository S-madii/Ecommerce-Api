import httpx
import pytest
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.models import User


async def _get_admin_headers(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    email: str = "admin@example.com",
) -> dict[str, str]:
    await client.post("/auth/signup", json={"email": email, "password": "Password123!"})
    await db_session.execute(update(User).where(User.email == email).values(role="admin"))
    await db_session.commit()
    resp = await client.post("/auth/login", json={"email": email, "password": "Password123!"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_create_product_rbac_and_sku_conflict(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
):
    await client.post("/auth/signup", json={"email": "customer@example.com", "password": "Password123!"})
    cust_login = await client.post("/auth/login", json={"email": "customer@example.com", "password": "Password123!"})
    customer_headers = {"Authorization": f"Bearer {cust_login.json()['access_token']}"}

    forbidden_cat = await client.post("/categories", json={"name": "Electronics"}, headers=customer_headers)
    assert forbidden_cat.status_code == 403

    headers = await _get_admin_headers(client, db_session)

    cat_resp = await client.post("/categories", json={"name": "Electronics"}, headers=headers)
    assert cat_resp.status_code == 201
    category_id = cat_resp.json()["id"]

    prod_payload = {
        "name": "Mechanical Keyboard",
        "sku": "KB-001",
        "description": "Tactile switches",
        "price": "120.00",
        "stock": 15,
        "category_id": category_id,
    }
    forbidden_prod = await client.post("/products", json=prod_payload, headers=customer_headers)
    assert forbidden_prod.status_code == 403

    prod_resp = await client.post("/products", json=prod_payload, headers=headers)
    assert prod_resp.status_code == 201
    assert prod_resp.json()["sku"] == "KB-001"
    assert prod_resp.json()["category"]["name"] == "Electronics"

    dup_resp = await client.post("/products", json=prod_payload, headers=headers)
    assert dup_resp.status_code == 409


@pytest.mark.asyncio
async def test_catalog_filtering_and_sorting(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
):
    headers = await _get_admin_headers(client, db_session)

    cat_resp = await client.post("/categories", json={"name": "Hardware"}, headers=headers)
    cat_id = cat_resp.json()["id"]

    products = [
        {"name": "Pro Gaming Mouse", "sku": "MS-01", "price": "50.00", "stock": 10, "category_id": cat_id},
        {"name": "Pro Gaming Monitor", "sku": "MN-01", "price": "300.00", "stock": 5, "category_id": cat_id},
        {"name": "Office Desk Lamp", "sku": "LP-01", "price": "25.00", "stock": 20, "category_id": None},
    ]
    for p in products:
        r = await client.post("/products", json=p, headers=headers)
        assert r.status_code == 201

    resp = await client.get("/products", params={"q": "Gaming", "sort": "price_asc"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert [item["sku"] for item in data["items"]] == ["MS-01", "MN-01"]

    price_resp = await client.get("/products", params={"min_price": "20.00", "max_price": "60.00", "sort": "price_asc"})
    assert price_resp.status_code == 200
    assert price_resp.json()["total"] == 2
    assert [item["sku"] for item in price_resp.json()["items"]] == ["LP-01", "MS-01"]

    bad_offset = await client.get("/products", params={"offset": 60000})
    assert bad_offset.status_code == 422


@pytest.mark.asyncio
async def test_redis_caching_and_invalidation(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
):
    headers = await _get_admin_headers(client, db_session)

    p1 = await client.post(
        "/products",
        json={"name": "Cached Headphones", "sku": "HP-01", "price": "80.00", "stock": 8, "category_id": None},
        headers=headers,
    )
    product_id = p1.json()["id"]

    detail_resp = await client.get(f"/products/{product_id}")
    assert detail_resp.status_code == 200
    cached_detail = await redis_client.get(f"product:{product_id}")
    assert cached_detail is not None

    list_resp = await client.get("/products")
    assert list_resp.status_code == 200
    list_keys_before = [k async for k in redis_client.scan_iter("products:list:*")]
    assert len(list_keys_before) == 1

    await client.post(
        "/products",
        json={"name": "USB Microphone", "sku": "MC-01", "price": "95.00", "stock": 4, "category_id": None},
        headers=headers,
    )
    list_keys_after = [k async for k in redis_client.scan_iter("products:list:*")]
    assert len(list_keys_after) == 0
