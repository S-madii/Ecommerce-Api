from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin
from app.db import get_db
from app.models import User
from app.schemas import CategoryCreate, CategoryRead
from app.services import CategoryService

router = APIRouter()


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    return await CategoryService.create_category(db, category)


@router.get("", response_model=list[CategoryRead])
async def read_categories(db: AsyncSession = Depends(get_db)):
    return await CategoryService.list_categories(db)
