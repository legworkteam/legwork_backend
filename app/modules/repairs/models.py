from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import RepairReservationStatus
from app.utils.datetime import now_kst
from app.utils.ids import new_uuid


def _enum_values(enum_cls) -> list[str]:
    return [member.value for member in enum_cls]


class RepairReservation(Base):
    __tablename__ = "repairReservation"
    __table_args__ = (
        Index("ix_repairReservation_diagnosisId_createdAt", "diagnosisId", "createdAt"),
        Index("ix_repairReservation_storeId_slot_status", "storeId", "slot", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    diagnosis_id: Mapped[UUID] = mapped_column(
        "diagnosisId",
        ForeignKey("diagnosis.id", ondelete="CASCADE"),
        nullable=False,
    )
    store_id: Mapped[UUID] = mapped_column("storeId", ForeignKey("store.id"), nullable=False)
    slot: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[RepairReservationStatus] = mapped_column(
        Enum(
            RepairReservationStatus,
            name="repair_reservation_status",
            values_callable=_enum_values,
        ),
        nullable=False,
        default=RepairReservationStatus.CONFIRMED,
    )
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column("cancelledAt", DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column("createdAt", DateTime(timezone=True), default=now_kst)
    updated_at: Mapped[datetime] = mapped_column(
        "updatedAt",
        DateTime(timezone=True),
        default=now_kst,
        onupdate=now_kst,
    )
