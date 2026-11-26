from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import CartItemCreate, CartItemRead, CartItemUpdate, CartRead
from app.services.cart import CartService

router = APIRouter()


@router.get("", response_model=CartRead)
async def read_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.get_cart(db, current_user.id)


@router.post("/items", response_model=CartRead, status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(
    item: CartItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.add_item(db, current_user.id, item)


@router.patch("/items/{item_id}", response_model=CartItemRead, status_code=status.HTTP_200_OK)
async def update_cart_item(
    item_id: int,
    item: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CartService.update_item_quantity(db, current_user.id, item_id, item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart_item(
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await CartService.delete_item(db, current_user.id, item_id)
    return None
