"""RegisteredProduct entity (Backend A).

Unifies purchased products (source=purchase, linked to an OrderItem) and
manually registered existing products (source=manual, with a serialNumber).
Both feed the same after-care flow. ProductCareGuide is added in a later phase.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UUIDMixin
from app.core.enums import RegisteredProductSource, pg_enum


class RegisteredProduct(UUIDMixin, Base):
    __tablename__ = "registeredProduct"
    __table_args__ = (
        Index("ix_registeredProduct_userId_createdAt", "userId", "createdAt"),
        Index("ix_registeredProduct_serialNumber", "serialNumber"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        "userId", ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        "productId", ForeignKey("product.id"), nullable=False
    )
    order_item_id: Mapped[uuid.UUID | None] = mapped_column(
        "orderItemId", ForeignKey("orderItem.id"), nullable=True
    )
    serial_number: Mapped[str | None] = mapped_column(
        "serialNumber", String(150), nullable=True
    )
    source: Mapped[RegisteredProductSource] = mapped_column(
        pg_enum(RegisteredProductSource, "registeredProductSource"), nullable=False
    )
    purchase_date: Mapped[date | None] = mapped_column(
        "purchaseDate", Date, nullable=True
    )
    nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
