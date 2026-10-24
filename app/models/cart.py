from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    cart_items: Mapped[list["CartItem"]] = relationship( back_populates="cart",)
    __table_args__ = (
        CheckConstraint("status IN ('active', 'converted', 'abandoned')", name="check_cart_status"),
        Index(
            "uq_carts_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active')")
        ) #One active cart per user
    )

class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)

    cart: Mapped["Cart"] = relationship( back_populates="cart_items",)
    product: Mapped["Product"] = relationship()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_cart_item_quantity"),
        UniqueConstraint('cart_id', 'product_id', name='uq_cart_product'),
        Index('idx_cart_items_product', 'product_id')
    )