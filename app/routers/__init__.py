from fastapi import APIRouter

from app.routers.auth import router as auth_router
from app.routers.categories import router as category_router
from app.routers.products import router as product_router
from app.routers.cart import router as cart_router
from app.routers.orders import router as order_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(category_router, prefix="/categories", tags=["categories"])
api_router.include_router(product_router, prefix="/products", tags=["products"])
api_router.include_router(cart_router, prefix="/cart", tags=["cart"])

api_router.include_router(order_router, prefix="/orders", tags=["orders"])

__all__ = ["api_router"]
