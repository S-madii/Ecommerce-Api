from uuid import UUID
from decimal import Decimal
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ShippingAddress(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    street: str
    city: str
    postal_code: str | None = None
    country: str = "Algeria"
    state: str | None = None


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    shipping_address: ShippingAddress


class OrderItemRead(BaseModel):
    id: int
    product_id: int | None
    product_name: str
    sku: str
    quantity: int
    unit_price: Decimal
    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    id: int
    public_id: UUID
    status: str
    currency: str
    subtotal: Decimal
    shipping_amount: Decimal
    total: Decimal
    shipping_address: ShippingAddress
    created_at: datetime
    items: list[OrderItemRead]
    model_config = ConfigDict(from_attributes=True)
