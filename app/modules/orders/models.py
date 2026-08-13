"""Order, OrderItem, Payment entities (Backend A).

OrderItem keeps snapshots (name/variant/unitPrice) so history survives later
catalog changes. Order 1-N Payment supports real-PG retries later. Orders and
payments are records — no hard delete.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.core.enums import OrderStatus, PaymentStatus, pg_enum


class Order(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "order"
    __table_args__ = ()

    user_id: Mapped[uuid.UUID] = mapped_column(
        "userId", ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        pg_enum(OrderStatus, "orderStatus"), nullable=False, default=OrderStatus.PENDING
    )
    total_amount: Mapped[int] = mapped_column("totalAmount", BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    paid_at: Mapped[datetime | None] = mapped_column(
        "paidAt", DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        "deletedAt", DateTime(timezone=True), nullable=True
    )


class OrderItem(UUIDMixin, Base):
    __tablename__ = "orderItem"

    order_id: Mapped[uuid.UUID] = mapped_column(
        "orderId", ForeignKey("order.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        "productId", ForeignKey("product.id"), nullable=False
    )
    variant_id: Mapped[uuid.UUID] = mapped_column(
        "variantId", ForeignKey("productVariant.id"), nullable=False
    )
    product_name_snapshot: Mapped[str] = mapped_column(
        "productNameSnapshot", String(255), nullable=False
    )
    variant_snapshot: Mapped[dict] = mapped_column(
        "variantSnapshot", JSONB, nullable=False
    )
    unit_price: Mapped[int] = mapped_column("unitPrice", BigInteger, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    line_amount: Mapped[int] = mapped_column("lineAmount", BigInteger, nullable=False)


class Payment(UUIDMixin, Base):
    __tablename__ = "payment"

    order_id: Mapped[uuid.UUID] = mapped_column(
        "orderId", ForeignKey("order.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(
        "providerPaymentId", String(255), nullable=True
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        pg_enum(PaymentStatus, "paymentStatus"), nullable=False
    )
    failure_code: Mapped[str | None] = mapped_column(
        "failureCode", String(60), nullable=True
    )
    failure_message: Mapped[str | None] = mapped_column(
        "failureMessage", String(255), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        "approvedAt", DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
