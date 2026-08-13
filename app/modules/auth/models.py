"""RefreshToken entity (Backend A).

Only the hash of a refresh token is stored (never the raw token). Rotation and
logout set revokedAt. Access tokens are stateless JWTs and are not stored.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, UUIDMixin


class RefreshToken(UUIDMixin, Base):
    __tablename__ = "refreshToken"

    user_id: Mapped[uuid.UUID] = mapped_column(
        "userId", ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(
        "tokenHash", String(255), nullable=False, unique=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        "expiresAt", DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        "revokedAt", DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "createdAt", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
