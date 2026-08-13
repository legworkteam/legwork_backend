"""Store and Campaign entities (Backend A).

QR opaque codes map to a Store/Campaign context only; they are unrelated to
product recognition. Repair reservations later reference Store via StoreService.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin


class Store(UUIDMixin, Base):
    __tablename__ = "store"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Campaign(UUIDMixin, Base):
    __tablename__ = "campaign"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(
        "startsAt", DateTime(timezone=True), nullable=True
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        "endsAt", DateTime(timezone=True), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class QrCodeMapping(UUIDMixin, Base):
    """Opaque QR code -> Store/Campaign context. Optional guest entry."""

    __tablename__ = "qrCodeMapping"

    code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    store_id: Mapped[uuid.UUID | None] = mapped_column(
        "storeId", ForeignKey("store.id"), nullable=True
    )
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(
        "campaignId", ForeignKey("campaign.id"), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        "expiresAt", DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
