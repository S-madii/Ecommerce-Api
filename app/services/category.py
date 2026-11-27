from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.models import Category
from app.schemas.category import CategoryCreate


class CategoryService:

    @staticmethod
    async def create_category(db: AsyncSession, category_in: CategoryCreate) -> Category:
        new_category = Category(name=category_in.name)
        db.add(new_category)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ConflictError(detail="Category with this name already exists")
        await db.refresh(new_category)
        return new_category

    @staticmethod
    async def list_categories(db: AsyncSession) -> list[Category]:
        result = await db.execute(select(Category).order_by(Category.name))
        return list(result.scalars().all())

    @staticmethod
    async def get_category_by_id(db: AsyncSession, category_id: int) -> Category:
        result = await db.execute(select(Category).where(Category.id == category_id))
        category = result.scalar_one_or_none()
        if not category:
            raise NotFoundError(detail="Category not found")
        return category
