from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import CheckoutRequest, CheckoutResponse
from app.services import OrderService

router = APIRouter()


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
        request: CheckoutRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    order, client_secret = await OrderService.checkout(
        db=db,
        user=current_user,
        shipping_address=request.shipping_address.model_dump(),
    )
    return CheckoutResponse(order=order, client_secret=client_secret)
