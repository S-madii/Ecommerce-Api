from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import OrderItem, Product, User, Order
from app.schemas import CheckoutRequest, OrderRead

from app.core.security import get_current_user
from app.db import get_db
from app.routers.cart import get_or_create_active_cart

router = APIRouter()


@router.post("/checkout", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def checkout(
        request: CheckoutRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    cart = await get_or_create_active_cart(current_user.id, db)
    if not cart.cart_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")
    product_ids = [item.product_id for item in cart.cart_items]
    product_ids = sorted(product_ids)
    stmt = (
        select(Product)
        .where(Product.id.in_(product_ids))
        .order_by(Product.id.asc())
        .with_for_update()
    )
    result = await db.execute(stmt)
    locked_products = result.scalars().all()
    if len(locked_products) != len(product_ids):
        await db.rollback()
        raise HTTPException(status_code=400, detail="One or more products are no longer available")
    products_by_id = {p.id: p for p in locked_products}
    for item in cart.cart_items:
        product = products_by_id[item.product_id]

        if product.stock < item.quantity:
            await db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}"
            )
    total_amount = Decimal('0.00')
    order_items_to_create = []
    for item in cart.cart_items:
        product = products_by_id[item.product_id]
        product.stock -= item.quantity
        line_subtotal = product.price * item.quantity
        total_amount += line_subtotal
        order_items_to_create.append(OrderItem(
            product_id=product.id,
            product_name=product.name,
            sku=product.sku,
            quantity=item.quantity,
            unit_price=product.price,
        ))
    order = Order(
        user_id=current_user.id,
        subtotal=total_amount,
        total=total_amount,
        shipping_address=request.shipping_address,
        items=order_items_to_create,
    )
    db.add(order)
    cart.status = 'converted'
    await db.commit()
    await db.refresh(order, attribute_names=["items"])
    return order
