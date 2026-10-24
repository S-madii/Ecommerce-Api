from fastapi import Depends, FastAPI, HTTPException

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import User

app = FastAPI(title="Commerce API")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"database": "ok"}
@app.get("/users/{user_id}")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "email": user.email,
        "created_at": user.created_at,
    }

