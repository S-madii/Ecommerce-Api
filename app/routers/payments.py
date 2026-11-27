from fastapi import APIRouter, Request, Header, Depends, HTTPException, status
import stripe as stripe

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderItem, Payment, Product, User

from app.db import get_db
from app.services import PaymentService, ProductService
from app.worker import send_order_confirmation_email

router = APIRouter()


async def _load_order_and_payment(db: AsyncSession, payment_intent: dict) -> tuple[Order, Payment]:
    order_id = payment_intent.get("metadata", {}).get("order_id")
    if not order_id:
        raise HTTPException(status_code=400, detail="Missing order_id in metadata")
    order = await db.get(Order, int(order_id))
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    result = await db.execute(select(Payment).where(Payment.provider_payment_id == payment_intent["id"]))
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return order, payment


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

    if event["type"] == "payment_intent.succeeded":
        order, payment_ = await _load_order_and_payment(db, event["data"]["object"])
        if payment_.status == "succeeded":
            return {"status": "Already Confirmed"}
        if order.status == "pending":
            order.status = "confirmed"
        payment_.status = "succeeded"
        user = await db.get(User, order.user_id)
        customer_email = user.email if user else None
        await db.commit()
        send_order_confirmation_email.delay(order.id, customer_email)
        return {"status": "success"}

    if event["type"] in ("payment_intent.payment_failed", "payment_intent.canceled"):
        order, payment_ = await _load_order_and_payment(db, event["data"]["object"])
        if payment_.status != "pending":
            return {"status": "Already Processed"}
        payment_.status = "cancelled" if event["type"] == "payment_intent.canceled" else "failed"
        product_ids: list[int] = []
        if order.status == "pending":
            order.status = "cancelled"
            items = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalars().all()
            for item in items:
                if item.product_id is not None:
                    product_ids.append(item.product_id)
                    await db.execute(
                        update(Product).where(Product.id == item.product_id)
                        .values(stock=Product.stock + item.quantity)
                    )
        await db.commit()
        await ProductService.invalidate_product_list_cache(product_ids)
        return {"status": "payment_failed_handled"}

    return {"status": "ignored"}
