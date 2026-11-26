from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from app.models import Order


async def _create_order_via_checkout(client: httpx.AsyncClient, intent_id: str = "pi_webhook_test_1") -> int:
    await client.post("/auth/signup", json={"email": "payer@example.com", "password": "Password123!"})
    login = await client.post("/auth/login", json={"email": "payer@example.com", "password": "Password123!"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    prod = await client.post(
        "/products",
        json={"name": "SSD 2TB", "sku": "SSD-2TB", "price": "150.00", "stock": 5, "category_id": None},
        headers=headers,
    )
    product_id = prod.json()["id"]
    await client.post("/cart/items", json={"product_id": product_id, "quantity": 1}, headers=headers)

    fake_intent = SimpleNamespace(id=intent_id, client_secret="pi_secret_xyz")
    with patch(
        "app.services.payment.PaymentService.create_payment_intent",
        new=AsyncMock(return_value=fake_intent),
    ):
        checkout_resp = await client.post(
            "/orders/checkout",
            json={"shipping_address": {"city": "Oran", "street": "42 Front de Mer"}},
            headers=headers,
        )
    assert checkout_resp.status_code == 201
    return checkout_resp.json()["order"]["id"]


@pytest.mark.asyncio
async def test_webhook_rejects_bad_signature(client: httpx.AsyncClient):
    with patch(
        "app.services.payment.PaymentService.verify_payment_intent",
        side_effect=stripe.error.SignatureVerificationError("Invalid signature", "t=123,v1=bad"),
    ):
        resp = await client.post(
            "/payments/webhook",
            content=b'{"type": "payment_intent.succeeded"}',
            headers={"Stripe-Signature": "t=123,v1=bad"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_confirms_order_and_dispatches_celery(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
):
    order_id = await _create_order_via_checkout(client, intent_id="pi_live_999")

    fake_stripe_event = {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_live_999",
                "metadata": {"order_id": str(order_id)},
            }
        },
    }

    with (
        patch("app.services.payment.PaymentService.verify_payment_intent", return_value=fake_stripe_event),
        patch("app.routers.payments.send_order_confirmation_email.delay") as mock_celery_delay,
    ):
        # 1st webhook delivery -> confirms order and triggers Celery task
        resp1 = await client.post(
            "/payments/webhook",
            content=b'{"id": "evt_1"}',
            headers={"Stripe-Signature": "t=123,v1=valid"},
        )
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "success"
        mock_celery_delay.assert_called_once_with(order_id)

        # 2nd duplicate webhook delivery -> idempotent (does NOT send duplicate email!)
        resp2 = await client.post(
            "/payments/webhook",
            content=b'{"id": "evt_1"}',
            headers={"Stripe-Signature": "t=123,v1=valid"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "Already Confirmed"
        assert mock_celery_delay.call_count == 1

    # Verify order status in PostgreSQL transitioned to 'confirmed'
    order_in_db = await db_session.get(Order, order_id)
    assert order_in_db is not None
    assert order_in_db.status == "confirmed"
