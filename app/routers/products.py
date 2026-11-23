from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import ProductCreate, ProductList, ProductRead
from app.services.product import ProductService

router = APIRouter()


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_product = await ProductService.create_product(db, product)
    await db.commit()
    await ProductService.invalidate_product_list_cache()
    return new_product


@router.get("", response_model=ProductList)
async def read_products(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0, le=50000),
    q: str | None = None,
    max_price: Decimal | None = Query(default=None, ge=0),
    min_price: Decimal | None = Query(default=None, ge=0),
    sort: Literal["price_asc", "price_desc", "newest"] = "newest",
    category_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await ProductService.list_products(
        db=db,
        limit=limit,
        offset=offset,
        q=q,
        min_price=min_price,
        max_price=max_price,
        sort=sort,
        category_id=category_id,
    )


@router.get("/{product_id}", response_model=ProductRead)
async def read_product(product_id: int, db: AsyncSession = Depends(get_db)):
    return await ProductService.get_product_by_id(db, product_id)
