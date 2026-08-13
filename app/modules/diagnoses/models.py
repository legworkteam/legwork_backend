from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import DamageSeverity, DiagnosisProviderKind
from app.utils.datetime import now_kst
from app.utils.ids import new_uuid


def _enum_values(enum_cls) -> list[str]:
    return [member.value for member in enum_cls]


class Diagnosis(Base):
    __tablename__ = "diagnosis"
    __table_args__ = (
        Index("ix_diagnosis_userId_createdAt", "userId", "createdAt"),
        Index("ix_diagnosis_registeredProductId_createdAt", "registeredProductId", "createdAt"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    user_id: Mapped[UUID] = mapped_column("userId", ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    registered_product_id: Mapped[UUID] = mapped_column(
        "registeredProductId",
        ForeignKey("registeredProduct.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_id: Mapped[UUID] = mapped_column("jobId", ForeignKey("job.id", ondelete="CASCADE"), unique=True, nullable=False)
    source_file_id: Mapped[UUID] = mapped_column("sourceFileId", nullable=False)
    provider: Mapped[DiagnosisProviderKind] = mapped_column(
        Enum(DiagnosisProviderKind, name="diagnosis_provider", values_callable=_enum_values),
        nullable=False,
    )
    repair_needed: Mapped[bool] = mapped_column("repairNeeded", Boolean, nullable=False, default=False)
    overall_condition: Mapped[str] = mapped_column("overallCondition", String(50), nullable=False)
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), default=now_kst)
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=True),
        default=now_kst,
        onupdate=now_kst,
    )


class Damage(Base):
    __tablename__ = "damage"
    __table_args__ = (Index("ix_damage_diagnosisId_sortOrder", "diagnosisId", "sortOrder"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    diagnosis_id: Mapped[UUID] = mapped_column(
        "diagnosisId",
        ForeignKey("diagnosis.id", ondelete="CASCADE"),
        nullable=False,
    )
    damage_type: Mapped[str] = mapped_column("damageType", String(80), nullable=False)
    area: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[DamageSeverity] = mapped_column(
        Enum(DamageSeverity, name="damage_severity", values_callable=_enum_values),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    repair_needed: Mapped[bool] = mapped_column("repairNeeded", Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column("sortOrder", Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), default=now_kst)
