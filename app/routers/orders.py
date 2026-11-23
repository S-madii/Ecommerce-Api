from fastapi import APIRouter, Depends, status, HTTPException

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.schemas import CheckoutRequest, CheckoutResponse

from app.core.security import get_current_user
from app.db import get_db
from app.services import OrderService
from app.core.exceptions import CheckoutError

router = APIRouter()


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout(
        request: CheckoutRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
):
    try:
        order, client_secret = await OrderService.checkout(
            db=db,
            user=current_user,
            shipping_address=request.shipping_address,
        )
        return CheckoutResponse(order=order, client_secret=client_secret)
    except CheckoutError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
