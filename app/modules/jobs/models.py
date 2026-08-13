from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, JSON, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import JobStatus, JobType
from app.utils.datetime import now_kst
from app.utils.ids import new_uuid


def _enum_values(enum_cls: type[JobType] | type[JobStatus]) -> list[str]:
    return [member.value for member in enum_cls]


class Job(Base):
    __tablename__ = "job"
    __table_args__ = (
        CheckConstraint(
            '(("userId" IS NOT NULL AND "guestSessionId" IS NULL) OR ("userId" IS NULL AND "guestSessionId" IS NOT NULL))',
            name="job_owner_xor",
        ),
        CheckConstraint('"progress" >= 0 AND "progress" <= 100', name="job_progress_range"),
        Index("ix_job_userId_createdAt", "userId", "createdAt"),
        Index("ix_job_guestSessionId_createdAt", "guestSessionId", "createdAt"),
        Index("ix_job_expiresAt", "expiresAt"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[UUID | None] = mapped_column("userId", nullable=True)
    guest_session_id: Mapped[UUID | None] = mapped_column("guestSessionId", nullable=True)
    type: Mapped[JobType] = mapped_column(Enum(JobType, name="job_type", values_callable=_enum_values))
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status", values_callable=_enum_values),
        default=JobStatus.PENDING,
    )
    progress: Mapped[int] = mapped_column(SmallInteger, default=0)
    result_json: Mapped[dict | None] = mapped_column("resultJson", JSON, nullable=True)
    error_json: Mapped[dict | None] = mapped_column("errorJson", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), default=now_kst)
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=True),
        default=now_kst,
        onupdate=now_kst,
    )
    expires_at: Mapped[datetime] = mapped_column("expiresAt", DateTime(timezone=True))
