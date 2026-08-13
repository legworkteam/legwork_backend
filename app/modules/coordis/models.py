from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UUIDMixin
from app.utils.datetime import now_kst


class SavedCoordi(UUIDMixin, Base):
    __tablename__ = "savedCoordi"
    __table_args__ = (
        Index("ix_savedCoordi_userId_deletedAt_createdAt", "userId", "deletedAt", "createdAt"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        "userId", ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    thumbnail_file_id: Mapped[uuid.UUID | None] = mapped_column("thumbnailFileId", nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), default=now_kst, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt", DateTime(timezone=True), default=now_kst, onupdate=now_kst, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column("deletedAt", DateTime(timezone=True), nullable=True)


class SavedCoordiItem(UUIDMixin, Base):
    __tablename__ = "savedCoordiItem"
    __table_args__ = (
        Index("ix_savedCoordiItem_savedCoordiId_sortOrder", "savedCoordiId", "sortOrder"),
    )

    saved_coordi_id: Mapped[uuid.UUID] = mapped_column(
        "savedCoordiId", ForeignKey("savedCoordi.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[uuid.UUID] = mapped_column("productId", ForeignKey("product.id"), nullable=False)
    variant_id: Mapped[uuid.UUID | None] = mapped_column("variantId", ForeignKey("productVariant.id"), nullable=True)
    sort_order: Mapped[int] = mapped_column("sortOrder", Integer, nullable=False)
