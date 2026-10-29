from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import User
from app.routers.auth import router as auth_router
from app.schemas.user import UserRead

app = FastAPI(title="Commerce API")
app.include_router(auth_router, prefix="/auth", tags=["auth"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"database": "ok"}


@app.get("/users/{user_id}", response_model=UserRead)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user
