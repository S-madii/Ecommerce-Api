import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
class Order(Base):
    __tablename__ = "orders"


    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    public_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), unique=True, nullable=False, server_default=text("gen_random_uuid()"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'pending'"))
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'DZD'"))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False, server_default=text("'0.00'"))
    total: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    shipping_address : Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    __table_args__ = (
        CheckConstraint("subtotal >= 0", name="chk_orders_subtotal"),
        CheckConstraint("shipping_amount >= 0", name="chk_orders_shipping_amount"),
        CheckConstraint("total >= 0", name="chk_orders_total"),
        Index("idx_orders_user_created", 'user_id', text("created_at DESC")),
        Index("idx_orders_status_created", 'status', text("created_at DESC")),
        CheckConstraint("status IN ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')",name="chk_orders_status")
    )

class OrderItem(Base):
    __tablename__ = "order_items"


    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"))
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    order: Mapped["Order"] = relationship(back_populates="items")
    __table_args__ = (
        CheckConstraint("quantity > 0", name="chk_order_items_quantity"),
        CheckConstraint("unit_price >= 0", name="chk_order_items_unit_price"),
        Index("idx_order_items_order", 'order_id' ),
        Index("idx_order_items_product", 'product_id' ),
    )

class Payment(Base):
    __tablename__ = "payments"


    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False, server_default=text("'DZD'"))
    status: Mapped[str] = mapped_column(String(30), nullable=False, server_default=text("'pending'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint("amount > 0", name="chk_payment_amount"),
        CheckConstraint("status IN ('pending', 'requires_action', 'succeeded', 'failed', 'cancelled', 'partially_refunded', 'refunded')", name="chk_payment_status"),
        CheckConstraint("LENGTH(TRIM(provider)) > 0", name="chk_payment_provider"),
        Index("uq_payment_provider_reference", 'provider', 'provider_payment_id', unique=True),
        Index("idx_payment_order", 'order_id'),
        Index("idx_payment_status", 'status')
    )



