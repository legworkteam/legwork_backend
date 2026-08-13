from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UUIDMixin
from app.core.enums import Gender, pg_enum


class Avatar(UUIDMixin, Base):
    __tablename__ = "avatar"
    __table_args__ = (
        UniqueConstraint("userId", name="uq_avatar_userId"),
        CheckConstraint('"heightCm" >= 100 AND "heightCm" <= 230', name="ck_avatar_height_range"),
        CheckConstraint('"weightKg" >= 30 AND "weightKg" <= 200', name="ck_avatar_weight_range"),
        Index("ix_avatar_previewFileId", "previewFileId"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        "userId", ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    height_cm: Mapped[float] = mapped_column("heightCm", Numeric, nullable=False)
    weight_kg: Mapped[float] = mapped_column("weightKg", Numeric, nullable=False)
    gender: Mapped[Gender] = mapped_column(pg_enum(Gender, "gender"), nullable=False)
    preview_file_id: Mapped[uuid.UUID | None] = mapped_column("previewFileId", nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt", DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
