from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.routers.auth import router as auth_router
from app.routers.categories import router as category_router
from app.routers.products import router as product_router

app = FastAPI(title="Commerce API")
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(category_router, prefix="/categories", tags=["categories"])

app.include_router(product_router, prefix="/products", tags=["products"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"database": "ok"}
