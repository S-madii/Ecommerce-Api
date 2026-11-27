from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import stripe

from app.models import Order, User


async def _create_order_via_checkout(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    intent_id: str = "pi_webhook_test_1",
) -> int:
    await client.post("/auth/signup", json={"email": "payer@example.com", "password": "Password123!"})
    await db_session.execute(update(User).where(User.email == "payer@example.com").values(role="admin"))
    await db_session.commit()
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
    order_id = await _create_order_via_checkout(client, db_session, intent_id="pi_live_999")

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
        resp1 = await client.post(
            "/payments/webhook",
            content=b'{"id": "evt_1"}',
            headers={"Stripe-Signature": "t=123,v1=valid"},
        )
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "success"
        mock_celery_delay.assert_called_once_with(order_id, "payer@example.com")

        resp2 = await client.post(
            "/payments/webhook",
            content=b'{"id": "evt_1"}',
            headers={"Stripe-Signature": "t=123,v1=valid"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "Already Confirmed"
        assert mock_celery_delay.call_count == 1

    order_in_db = await db_session.get(Order, order_id)
    assert order_in_db is not None
    assert order_in_db.status == "confirmed"


@pytest.mark.asyncio
async def test_payment_intent_uses_order_currency():
    from decimal import Decimal
    from app.services.payment import PaymentService

    order = Order(id=7, total=Decimal("12.50"), currency="USD")
    with patch("app.services.payment.stripe.PaymentIntent.create") as mock_create:
        mock_create.return_value = SimpleNamespace(id="pi_x", client_secret="s")
        await PaymentService.create_payment_intent(order)
    kwargs = mock_create.call_args.kwargs
    assert kwargs["currency"] == "usd"
    assert kwargs["amount"] == 1250


@pytest.mark.asyncio
async def test_webhook_real_signature_verification(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
):
    """No mocking of verify_payment_intent: exercises the real Stripe HMAC check."""
    import json
    import time

    from pydantic import SecretStr

    from app.core.config import settings

    secret = "whsec_unit_test_secret"
    monkeypatch.setattr(settings, "STRIPE_WEBHOOK_SECRET", SecretStr(secret))

    order_id = await _create_order_via_checkout(client, db_session, intent_id="pi_real_sig_1")
    payload = json.dumps({
        "id": "evt_real_sig",
        "object": "event",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_real_sig_1", "metadata": {"order_id": str(order_id)}}},
    }).encode()

    ts = int(time.time())
    sig = stripe.WebhookSignature._compute_signature(f"{ts}.{payload.decode()}", secret)
    good = {"Stripe-Signature": f"t={ts},v1={sig}"}
    bad = {"Stripe-Signature": f"t={ts},v1={'0' * 64}"}

    with patch("app.routers.payments.send_order_confirmation_email.delay") as delay:
        assert (await client.post("/payments/webhook", content=payload, headers=bad)).status_code == 400
        delay.assert_not_called()
        ok = await client.post("/payments/webhook", content=payload, headers=good)
        assert ok.status_code == 200
        assert ok.json()["status"] == "success"
        delay.assert_called_once_with(order_id, "payer@example.com")


@pytest.mark.asyncio
async def test_webhook_payment_failed_cancels_order_and_restores_stock(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
):
    from app.models import Payment, Product

    order_id = await _create_order_via_checkout(client, db_session, intent_id="pi_fail_1")
    await db_session.rollback()
    product = (await db_session.execute(select(Product).where(Product.sku == "SSD-2TB"))).scalar_one()
    assert product.stock == 4  # 5 - 1 reserved at checkout

    event = {
        "type": "payment_intent.payment_failed",
        "data": {"object": {"id": "pi_fail_1", "metadata": {"order_id": str(order_id)}}},
    }
    with (
        patch("app.services.payment.PaymentService.verify_payment_intent", return_value=event),
        patch("app.routers.payments.send_order_confirmation_email.delay") as delay,
    ):
        r1 = await client.post("/payments/webhook", content=b"{}", headers={"Stripe-Signature": "x"})
        r2 = await client.post("/payments/webhook", content=b"{}", headers={"Stripe-Signature": "x"})
        delay.assert_not_called()
    assert r1.json()["status"] == "payment_failed_handled"
    assert r2.json()["status"] == "Already Processed"  # idempotent: stock not restored twice

    db_session.expire_all()
    order = await db_session.get(Order, order_id)
    payment = (await db_session.execute(select(Payment).where(Payment.order_id == order_id))).scalar_one()
    product = (await db_session.execute(select(Product).where(Product.sku == "SSD-2TB"))).scalar_one()
    assert order.status == "cancelled"
    assert payment.status == "failed"
    assert product.stock == 5


@pytest.mark.asyncio
async def test_webhook_payment_canceled_cancels_order_and_restores_stock(
    client: httpx.AsyncClient,
    db_session: AsyncSession,
):
    from app.models import Payment, Product

    order_id = await _create_order_via_checkout(client, db_session, intent_id="pi_cancel_1")
    event = {
        "type": "payment_intent.canceled",
        "data": {"object": {"id": "pi_cancel_1", "metadata": {"order_id": str(order_id)}}},
    }
    with patch("app.services.payment.PaymentService.verify_payment_intent", return_value=event):
        r1 = await client.post("/payments/webhook", content=b"{}", headers={"Stripe-Signature": "x"})
        r2 = await client.post("/payments/webhook", content=b"{}", headers={"Stripe-Signature": "x"})
    assert r1.json()["status"] == "payment_failed_handled"
    assert r2.json()["status"] == "Already Processed"

    db_session.expire_all()
    order = await db_session.get(Order, order_id)
    payment = (await db_session.execute(select(Payment).where(Payment.order_id == order_id))).scalar_one()
    product = (await db_session.execute(select(Product).where(Product.sku == "SSD-2TB"))).scalar_one()
    assert order.status == "cancelled"
    assert payment.status == "cancelled"
    assert product.stock == 5
