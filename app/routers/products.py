from fastapi import APIRouter, Depends, HTTPException, status, Query
from app.core.exceptions import NotFoundError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.schemas.product import ProductCreate, ProductRead
from app.models import Product, Category, User

from app.db.session import get_db
from app.core.security import get_current_user

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
    new_product = Product(name=product.name, stock=product.stock, description=product.description, price=product.price,
                          category_id=product.category_id, sku=product.sku)
    db.add(new_product)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product with this SKU already exists")
    await db.refresh(new_product, attribute_names=["category"])
    return new_product


@router.get("", response_model=list[ProductRead])
async def read_products(limit: int = Query(default=20, ge=1, le=100),
                        offset: int = Query(default=0, ge=0),
                        category_id: int | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Product).options(selectinload(Product.category))
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    query = query.order_by(Product.name).limit(limit).offset(offset)
    result = await db.execute(query)
    products = result.scalars().all()
    return products


@router.get("/{product_id}", response_model=ProductRead)
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product).options(selectinload(Product.category)).where(Product.id == product_id,
                                                                                            Product.is_active == True))
    product = result.scalar_one_or_none()
    if not product:
        raise NotFoundError(detail="Product not found")
    return product
