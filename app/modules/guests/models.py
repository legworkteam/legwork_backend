"""GuestSession entity (Backend A).

A guest session may be created with or without a QR context. It optionally
holds body parameters (height/weight/gender) used for avatar try-on, and
counts photo try-on attempts (max 3). Expires at 23:59:59 KST of creation day.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UUIDMixin
from app.core.enums import Gender, pg_enum


class GuestSession(UUIDMixin, Base):
    __tablename__ = "guestSession"

    qr_code_id: Mapped[uuid.UUID | None] = mapped_column(
        "qrCodeId", ForeignKey("qrCodeMapping.id"), nullable=True
    )
    height_cm: Mapped[float | None] = mapped_column("heightCm", Numeric, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column("weightKg", Numeric, nullable=True)
    gender: Mapped[Gender | None] = mapped_column(pg_enum(Gender, "gender"), nullable=True)
    photo_try_on_count: Mapped[int] = mapped_column(
        "photoTryOnCount", Integer, nullable=False, default=0
    )
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        "expiresAt", DateTime(timezone=True), nullable=False
    )
