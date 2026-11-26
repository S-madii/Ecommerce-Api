from decimal import Decimal
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import ConflictError, NotFoundError
from app.core.redis import redis_client
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
            await db.flush()
        except IntegrityError:
            await db.rollback()
            raise ConflictError(detail="Product with this SKU already exists")
        await db.refresh(new_product, attribute_names=["category"])
        return new_product

    @staticmethod
    async def invalidate_product_list_cache(product_ids: list[int] | None = None) -> None:
        keys = [key async for key in redis_client.scan_iter("products:list:*")]
        if product_ids:
            keys.extend(f"product:{pid}" for pid in product_ids if pid is not None)
        if keys:
            await redis_client.delete(*keys)

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
        cache_key = f"products:list:{limit}:{offset}:{q}:{category_id}:{min_price}:{max_price}:{sort}"
        cached = await redis_client.get(cache_key)
        if cached:
            return ProductList.model_validate_json(cached)
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
        product_list = ProductList(
            items=[ProductRead.model_validate(p) for p in products],
            total=total,
            limit=limit,
            offset=offset,
        )
        await redis_client.set(cache_key, product_list.model_dump_json(), ex=60)  # 60 seconds TTL
        return product_list

    @staticmethod
    async def get_product_by_id(db: AsyncSession, product_id: int) -> ProductRead:
        cache_key = f"product:{product_id}"
        cached = await redis_client.get(cache_key)
        if cached:
            return ProductRead.model_validate_json(cached)
        query = (
            select(Product)
            .options(selectinload(Product.category))
            .where(Product.id == product_id, Product.is_active == True)
        )
        result = await db.execute(query)
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError(detail="Product not found")
        product_schema = ProductRead.model_validate(product)
        await redis_client.set(f"product:{product_id}", product_schema.model_dump_json(), ex=3600)
        return product
