"""User entity (Backend A).

Same email under LOCAL / GOOGLE / KAKAO produces separate accounts; email is
never used alone to merge. LOCAL accounts carry a bcrypt passwordHash; social
accounts carry providerUserId. Soft-deleted via deletedAt.
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, UUIDMixin
from app.core.enums import AuthProvider, pg_enum


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user"
    __table_args__ = (
        # Google/Kakao identity uniqueness; LOCAL email uniqueness is enforced
        # via a partial index created in the migration (active accounts only).
        UniqueConstraint("authProvider", "providerUserId", name="uq_user_provider_identity"),
    )

    name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[AuthProvider] = mapped_column(
        "authProvider", pg_enum(AuthProvider, "authProvider"), nullable=False
    )
    provider_user_id: Mapped[str | None] = mapped_column(
        "providerUserId", String(255), nullable=True
    )
    password_hash: Mapped[str | None] = mapped_column("passwordHash", String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    login_fail_count: Mapped[int] = mapped_column(
        "loginFailCount", Integer, nullable=False, default=0
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        "lockedUntil", DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        "deletedAt", DateTime(timezone=True), nullable=True
    )
