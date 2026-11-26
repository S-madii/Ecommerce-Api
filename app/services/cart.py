from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError, InsufficientStockError
from app.models import Cart, CartItem, Product
from app.schemas import CartItemCreate, CartItemRead, CartItemUpdate, CartRead


class CartService:

    @staticmethod
    async def get_or_create_active_cart(db: AsyncSession, user_id: int) -> Cart:
        stmt = (
            select(Cart)
            .options(selectinload(Cart.cart_items).selectinload(CartItem.product))
            .where(Cart.user_id == user_id, Cart.status == "active")
        )
        result = await db.execute(stmt)
        cart = result.scalar_one_or_none()

        if not cart:
            cart = Cart(user_id=user_id, status="active")
            db.add(cart)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
            result = await db.execute(stmt)
            cart = result.scalar_one()

        return cart

    @staticmethod
    async def get_cart(db: AsyncSession, user_id: int) -> CartRead:
        cart = await CartService.get_or_create_active_cart(db, user_id)
        items_out = []
        total = Decimal("0.00")

        for item in cart.cart_items:
            subtotal = Decimal(str(item.product.price)) * item.quantity
            total += subtotal
            items_out.append(CartItemRead(
                id=item.id,  # type: ignore[arg-type]
                product_id=item.product_id,  # type: ignore[arg-type]
                quantity=item.quantity,  # type: ignore[arg-type]
                unit_price=Decimal(str(item.product.price)),
                subtotal=subtotal,
                product_name=str(item.product.name),
            ))

        return CartRead(
            id=cart.id,
            items=items_out,
            total=total,
        )

    @staticmethod
    async def add_item(db: AsyncSession, user_id: int, item_in: CartItemCreate) -> CartRead:
        stmt = select(Product).where(Product.id == item_in.product_id, Product.is_active == True)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError(detail="Product not found")

        cart = await CartService.get_or_create_active_cart(db, user_id)
        for cart_item in cart.cart_items:
            if cart_item.product.id == product.id:
                if cart_item.quantity + item_in.quantity > product.stock:
                    raise InsufficientStockError(product.name)
                cart_item.quantity += item_in.quantity
                await db.commit()
                return await CartService.get_cart(db, user_id)

        if item_in.quantity > product.stock:
            raise InsufficientStockError(product.name)

        new_item = CartItem(
            cart_id=cart.id,
            product_id=product.id,
            quantity=item_in.quantity,
        )
        db.add(new_item)
        await db.commit()
        return await CartService.get_cart(db, user_id)

    @staticmethod
    async def update_item_quantity(
        db: AsyncSession,
        user_id: int,
        item_id: int,
        item_in: CartItemUpdate,
    ) -> CartItemRead:
        cart = await CartService.get_or_create_active_cart(db, user_id)
        stmt = select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
        result = await db.execute(stmt)
        cart_item = result.scalar_one_or_none()
        if not cart_item:
            raise NotFoundError(detail="Cart item not found")

        product_stmt = select(Product).where(Product.id == cart_item.product_id, Product.is_active == True)
        product_result = await db.execute(product_stmt)
        product = product_result.scalar_one_or_none()
        if product is None:
            raise NotFoundError(detail="Product is deactivated or missing")

        if item_in.quantity > product.stock:
            raise InsufficientStockError(product.name)

        cart_item.quantity = item_in.quantity
        await db.commit()
        return CartItemRead(
            id=cart_item.id,  # type: ignore[arg-type]
            product_id=cart_item.product_id,  # type: ignore[arg-type]
            quantity=cart_item.quantity,  # type: ignore[arg-type]
            unit_price=Decimal(str(product.price)),
            subtotal=Decimal(str(product.price)) * cart_item.quantity,  # type: ignore[operator]
            product_name=str(product.name),
        )

    @staticmethod
    async def delete_item(db: AsyncSession, user_id: int, item_id: int) -> None:
        cart = await CartService.get_or_create_active_cart(db, user_id)
        stmt = select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
        result = await db.execute(stmt)
        cart_item = result.scalar_one_or_none()
        if not cart_item:
            raise NotFoundError(detail="Cart item not found")

        await db.delete(cart_item)
        await db.commit()
