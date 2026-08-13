from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import TryOnProviderKind, TryOnScope
from app.utils.datetime import now_kst
from app.utils.ids import new_uuid


def _enum_values(enum_cls: type[TryOnScope] | type[TryOnProviderKind]) -> list[str]:
    return [member.value for member in enum_cls]


class TryOn(Base):
    __tablename__ = "tryOn"
    __table_args__ = (
        CheckConstraint(
            '(("userId" IS NOT NULL AND "guestSessionId" IS NULL) OR ("userId" IS NULL AND "guestSessionId" IS NOT NULL))',
            name="try_on_owner_xor",
        ),
        Index("ix_tryOn_userId_createdAt", "userId", "createdAt"),
        Index("ix_tryOn_guestSessionId_createdAt", "guestSessionId", "createdAt"),
        Index("ix_tryOn_savedAt", "savedAt"),
        Index("ix_tryOn_expiresAt", "expiresAt"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[UUID | None] = mapped_column("userId", ForeignKey("user.id", ondelete="CASCADE"), nullable=True)
    guest_session_id: Mapped[UUID | None] = mapped_column(
        "guestSessionId", ForeignKey("guestSession.id", ondelete="CASCADE"), nullable=True
    )
    job_id: Mapped[UUID] = mapped_column("jobId", ForeignKey("job.id", ondelete="CASCADE"), nullable=False, unique=True)
    scope: Mapped[TryOnScope] = mapped_column(
        Enum(TryOnScope, name="try_on_scope", values_callable=_enum_values),
        nullable=False,
    )
    product_id: Mapped[UUID | None] = mapped_column("productId", ForeignKey("product.id"), nullable=True)
    saved_coordi_id: Mapped[UUID | None] = mapped_column("savedCoordiId", ForeignKey("savedCoordi.id"), nullable=True)
    result_file_id: Mapped[UUID] = mapped_column("resultFileId", nullable=False)
    provider: Mapped[TryOnProviderKind] = mapped_column(
        Enum(TryOnProviderKind, name="try_on_provider", values_callable=_enum_values),
        nullable=False,
    )
    request_json: Mapped[dict | None] = mapped_column("requestJson", JSON, nullable=True)
    saved_at: Mapped[datetime | None] = mapped_column("savedAt", DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column("expiresAt", DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), default=now_kst)
