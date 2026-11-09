from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.category import CategoryRead


class ProductCreate(BaseModel):
    sku: str
    name: str
    description: str | None = None
    price: Decimal = Field(gt=0, decimal_places=2)
    category_id: int | None = None
    stock: int = Field(default=0, ge=0)
    is_active: bool = True


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str
    description: str | None = None
    price: Decimal
    category_id: int | None = None
    stock: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    category: "CategoryRead | None" = None


class ProductList(BaseModel):
    items: list[ProductRead]
    total: int
    limit: int
    offset: int
