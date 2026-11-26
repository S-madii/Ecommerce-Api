import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Product


async def _register_and_login(client: httpx.AsyncClient, email: str) -> dict[str, str]:
    await client.post("/auth/signup", json={"email": email, "password": "Password123!"})
    resp = await client.post("/auth/login", json={"email": email, "password": "Password123!"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.mark.asyncio
async def test_checkout_empty_cart_rejected(client: httpx.AsyncClient):
    headers = await _register_and_login(client, "empty@example.com")

    resp = await client.post(
        "/orders/checkout",
        json={"shipping_address": {"city": "Algiers", "street": "123 Didouche Mourad"}},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_concurrent_checkout_prevents_overselling(
        client: httpx.AsyncClient,
        db_session: AsyncSession,
):
    headers_a = await _register_and_login(client, "buyer_a@example.com")
    headers_b = await _register_and_login(client, "buyer_b@example.com")

    prod_resp = await client.post(
        "/products",
        json={
            "name": "RTX 5090 Founders Edition",
            "sku": "GPU-5090",
            "price": "1999.00",
            "stock": 1,
            "category_id": None,
        },
        headers=headers_a,
    )
    assert prod_resp.status_code == 201
    product_id = prod_resp.json()["id"]

    r_a = await client.post("/cart/items", json={"product_id": product_id, "quantity": 1}, headers=headers_a)
    r_b = await client.post("/cart/items", json={"product_id": product_id, "quantity": 1}, headers=headers_b)
    assert r_a.status_code == 201
    assert r_b.status_code == 201

    checkout_payload = {"shipping_address": {"city": "Algiers", "street": "1 Rue Emir Abdelkader"}}

    fake_intent = SimpleNamespace(id="pi_test_concurrent_123", client_secret="pi_test_secret_123")
    with patch(
            "app.services.payment.PaymentService.create_payment_intent",
            new=AsyncMock(return_value=fake_intent),
    ):
        resp_a, resp_b = await asyncio.gather(
            client.post("/orders/checkout", json=checkout_payload, headers=headers_a),
            client.post("/orders/checkout", json=checkout_payload, headers=headers_b),
        )

    statuses = sorted([resp_a.status_code, resp_b.status_code])
    assert statuses == [201, 400]

    product_in_db = await db_session.get(Product, product_id)
    assert product_in_db is not None
    assert product_in_db.stock == 0
