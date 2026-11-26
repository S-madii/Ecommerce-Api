import asyncio

import stripe
from app.core import settings
from app.models import Order


class PaymentService:
    @staticmethod
    async def create_payment_intent(order: Order):
        stripe.api_key = settings.STRIPE_SECRET_KEY.get_secret_value()
        amount_cents = int((order.total * 100).to_integral_value())
        intent = await asyncio.to_thread(
            stripe.PaymentIntent.create,
            amount=amount_cents,
            currency="usd",
            metadata={"order_id": str(order.id)},
        )
        return intent

    @staticmethod
    def verify_payment_intent(payload: bytes, sig_header: str):
        if not settings.STRIPE_SECRET_KEY:
            raise ValueError("Stripe secret key is not configured")
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise ValueError("STRIPE_WEBHOOK_SECRET is not configured")
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=settings.STRIPE_WEBHOOK_SECRET.get_secret_value()
        )
        return event
