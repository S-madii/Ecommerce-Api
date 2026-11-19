from pydantic import BaseModel

from app.schemas.order import OrderRead


class CheckoutResponse(BaseModel):
    order: OrderRead
    client_secret: str
