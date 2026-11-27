import asyncio

import stripe
from app.core import settings
from app.models import Order


class PaymentService:
    @staticmethod
    async def create_payment_intent(order: Order):
        stripe.api_key = settings.STRIPE_SECRET_KEY.get_secret_value()
        amount_cents = int((order.total * 100).to_integral_value())
        currency = order.currency.strip().lower()
        intent = await asyncio.to_thread(
            stripe.PaymentIntent.create,
            amount=amount_cents,
            currency=currency,
            metadata={"order_id": str(order.id)},
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
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
        # StripeObject is not a dict (no .get); normalise so callers can use plain dict access.
        return event.to_dict() if hasattr(event, "to_dict") else event
