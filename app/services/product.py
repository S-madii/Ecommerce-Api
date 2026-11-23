from decimal import Decimal
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models import Category, Product
from app.schemas import ProductCreate, ProductList, ProductRead


class ProductService:

    @staticmethod
    async def create_product(db: AsyncSession, product_in: ProductCreate) -> Product:
        if product_in.category_id is not None:
            result = await db.execute(select(Category).where(Category.id == product_in.category_id))
            category = result.scalar_one_or_none()
            if not category:
                raise NotFoundError(detail="Category not found")

        new_product = Product(
            name=product_in.name,
            stock=product_in.stock,
            description=product_in.description or "",
            price=product_in.price,
            category_id=product_in.category_id,
            sku=product_in.sku,
        )
        db.add(new_product)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Product with this SKU already exists",
            )
        await db.refresh(new_product, attribute_names=["category"])
        return new_product

    @staticmethod
    async def list_products(
        db: AsyncSession,
        limit: int = 20,
        offset: int = 0,
        q: str | None = None,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
        sort: Literal["price_asc", "price_desc", "newest"] = "newest",
        category_id: int | None = None,
    ) -> ProductList:
        conditions = [Product.is_active == True]
        if q is not None:
            conditions.append(Product.name.icontains(q, autoescape=True))
        if max_price is not None:
            conditions.append(Product.price <= max_price)
        if min_price is not None:
            conditions.append(Product.price >= min_price)
        if category_id is not None:
            conditions.append(Product.category_id == category_id)

        SORT_MAP = {
            "price_asc": Product.price.asc(),
            "price_desc": Product.price.desc(),
            "newest": Product.created_at.desc(),
        }
        sort_criterion = SORT_MAP[sort]

        count_stmt = select(func.count()).select_from(Product).where(*conditions)
        total = await db.scalar(count_stmt) or 0

        query = (
            select(Product)
            .options(selectinload(Product.category))
            .where(*conditions)
            .order_by(sort_criterion, Product.id.asc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(query)
        products = result.scalars().all()

        return ProductList(
            items=[ProductRead.model_validate(p) for p in products],
            total=total,
            limit=limit,
            offset=offset,
        )

    @staticmethod
    async def get_product_by_id(db: AsyncSession, product_id: int) -> Product:
        query = (
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == product_id, Product.is_active == True)
        )
        result = await db.execute(query)
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError(detail="Product not found")
        return product
