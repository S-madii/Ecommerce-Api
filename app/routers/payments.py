import http

from fastapi import APIRouter, Request, Header, Depends, HTTPException, status
import stripe as stripe

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, Payment
from app.schemas import payment

from app.db import get_db
from app.services import PaymentService

router = APIRouter()


@router.post("/webhook", status_code=status.HTTP_200_OK)
async def stripe_webhook(
        request: Request,
        stripe_signature: str = Header(None, alias="Stripe-Signature"),
        db: AsyncSession = Depends(get_db)
):
    payload = await request.body()
    try:
        event = PaymentService.verify_payment_intent(payload, stripe_signature)
    except(ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Bad request")
    if event["type"] != "payment_intent.succeeded":
        return {"status": "ignored"}
    payment_intent = event["data"]["object"]
    order_id = payment_intent["metadata"].get("order_id")
    order = await db.get(Order, int(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status == "pending":
        order.status = "confirmed"
    stmt = select(Payment).where(Payment.provider_payment_id == payment_intent["id"])
    result = await db.execute(stmt)
    payment_ = result.scalar_one_or_none()
    if not payment_:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment_.status == "succeeded":
        return {"status": "Already Confirmed"}
    payment_.status = "succeeded"
    await db.commit()
    return {"status": "success"}
