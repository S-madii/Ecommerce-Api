from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.models import Category, User
from app.schemas import CategoryCreate, CategoryRead

router = APIRouter()


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(category: CategoryCreate, db: AsyncSession = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    new_category = Category(name=category.name)
    db.add(new_category)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Category with this name already exists")
    await db.refresh(new_category)
    return new_category


@router.get("", response_model=list[CategoryRead])
async def read_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Category).order_by(Category.name))
    categories = result.scalars().all()
    return categories
