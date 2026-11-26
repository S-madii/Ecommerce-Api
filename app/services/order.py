from decimal import Decimal

from typing import Any, Dict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import EmptyCartError, InsufficientStockError, CheckoutError
from app.models import Cart, CartItem, Order, OrderItem, Payment, Product, User
from app.services.payment import PaymentService
from app.services.product import ProductService


class OrderService:

    @staticmethod
    async def _get_active_cart(db: AsyncSession, user_id: int) -> Cart:
        stmt = (
            select(Cart)
            .options(selectinload(Cart.cart_items).selectinload(CartItem.product))
            .where(Cart.user_id == user_id, Cart.status == "active")
        )
        result = await db.execute(stmt)
        cart = result.scalar_one_or_none()

        if not cart or not cart.cart_items:
            raise EmptyCartError("Cannot checkout an empty cart")
        return cart

    @staticmethod
    async def _reserve_inventory_and_create_order(
            db: AsyncSession,
            user_id: int,
            cart: Cart,
            shipping_address: Dict[str, Any],
    ) -> Order:
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
            raise CheckoutError("One or more products are no longer available")
        products_by_id = {p.id: p for p in locked_products}
        for item in cart.cart_items:
            product = products_by_id[item.product_id]

            if product.stock < item.quantity:
                await db.rollback()
                raise InsufficientStockError(product.name)
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
            user_id=user_id,
            subtotal=total_amount,
            total=total_amount,
            shipping_address=shipping_address,
            items=order_items_to_create,
        )
        db.add(order)
        cart.status = 'converted'
        await db.commit()
        await db.refresh(order, attribute_names=["items"])
        return order

    @staticmethod
    async def checkout(
            db: AsyncSession,
            user: User,
            shipping_address: Dict[str, Any],
    ) -> tuple[Order, str]:
        cart = await OrderService._get_active_cart(db, user.id)
        order = await OrderService._reserve_inventory_and_create_order(
            db,
            user.id,
            cart,
            shipping_address,
        )
        try:
            intent = await PaymentService.create_payment_intent(order)
        except Exception as e:
            order.status = "cancelled"
            for item in order.items:
                await db.execute(
                    update(Product)
                    .where(Product.id == item.product_id)
                    .values(stock=Product.stock + item.quantity)
                )
            await db.commit()
            await ProductService.invalidate_product_list_cache(
                [item.product_id for item in order.items if item.product_id is not None]
            )
            raise CheckoutError("Failed to create payment intent") from e
        payment = Payment(
            order_id=order.id,
            provider='stripe',
            provider_payment_id=intent.id,
            amount=order.total,
            status='pending',
        )
        db.add(payment)
        await db.commit()
        await ProductService.invalidate_product_list_cache(
            [item.product_id for item in order.items if item.product_id is not None]
        )
        await db.refresh(order, attribute_names=["items"])
        return order, intent.client_secret
