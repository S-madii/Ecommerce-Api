from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.exceptions import NotFoundError
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.schemas.product import ProductCreate, ProductRead, ProductList
from app.models import Product, Category, User
from decimal import Decimal
from app.db.session import get_db
from app.core.security import get_current_user
from typing import Literal

router = APIRouter()


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(product: ProductCreate, db: AsyncSession = Depends(get_db),
                         current_user: User = Depends(get_current_user)):
    # Check if the category exists
    if product.category_id is not None:
        result = await db.execute(select(Category).where(Category.id == product.category_id))
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundError(detail="Category not found")
    new_product = Product(name=product.name, stock=product.stock, description=product.description or "",
                          price=product.price,
                          category_id=product.category_id, sku=product.sku)
    db.add(new_product)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product with this SKU already exists")
    await db.refresh(new_product, attribute_names=["category"])
    return new_product


@router.get("", response_model=ProductList)
async def read_products(limit: int = Query(default=20, ge=1, le=100),
                        offset: int = Query(default=0, ge=0), q: str | None = None,
                        max_price: Decimal | None = Query(default=None, ge=0),
                        min_price: Decimal | None = Query(default=None, ge=0),
                        sort: Literal["price_asc", "price_desc", "newest"] = "newest",
                        category_id: int | None = None, db: AsyncSession = Depends(get_db)):
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
    query = select(Product).options(selectinload(Product.category)).where(*conditions).order_by(sort_criterion,
                                                                                                Product.id.asc()).limit(
        limit).offset(offset)
    result = await db.execute(query)
    products = result.scalars().all()
    return ProductList(items=products, total=total, limit=limit, offset=offset)


@router.get("/{product_id}", response_model=ProductRead)
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).options(selectinload(Product.category)).where(Product.id == product_id,
                                                                                            Product.is_active == True))
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError(detail="Product not found")
    return product
