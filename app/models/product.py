from decimal import Decimal

from sqlalchemy import ForeignKey, Index, BigInteger, Boolean, Numeric,DateTime, String, func, Identity, CheckConstraint, Text
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    stock: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    category: Mapped["Category | None"] = relationship(back_populates="products")

    __table_args__ = (

        CheckConstraint("LENGTH(TRIM(name)) > 0", name="chk_products_name"),
        CheckConstraint("stock >= 0", name="chk_products_stock"),
        CheckConstraint("price >= 0", name="chk_products_price"),
        Index("idx_products_category", "category_id"),
        Index("idx_products_active", "is_active"),
    )