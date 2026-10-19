from sqlalchemy import ForeignKey, Index, BigInteger, DateTime, String, func, Identity, text, UniqueConstraint, CheckConstraint
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, ondelete="CASCADE")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed', 'abandoned')", name="check_cart_status"),
        Index(
            "uq_carts_user_product",
            "user_id",
            "status",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id"), nullable=False, ondelete="CASCADE")
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, ondelete="CASCADE")
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_cart_item_quantity"),
        UniqueConstraint('cart_id', 'product_id', name='uq_cart_product'),
        Index('idx_cart_items_product', 'product_id'),
    )