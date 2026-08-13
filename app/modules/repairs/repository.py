from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RepairReservationStatus
from app.modules.diagnoses.models import Diagnosis
from app.modules.repairs.models import RepairReservation


class RepairReservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, reservation: RepairReservation) -> RepairReservation:
        self.session.add(reservation)
        await self.session.flush()
        await self.session.refresh(reservation)
        return reservation

    async def get_owned_by_id(
        self,
        *,
        reservation_id: UUID,
        user_id: UUID,
    ) -> RepairReservation | None:
        return await self.session.scalar(
            select(RepairReservation)
            .join(Diagnosis, Diagnosis.id == RepairReservation.diagnosis_id)
            .where(
                RepairReservation.id == reservation_id,
                Diagnosis.user_id == user_id,
            )
        )

    async def list_owned(self, *, user_id: UUID) -> list[RepairReservation]:
        result = await self.session.scalars(
            select(RepairReservation)
            .join(Diagnosis, Diagnosis.id == RepairReservation.diagnosis_id)
            .where(Diagnosis.user_id == user_id)
            .order_by(RepairReservation.created_at.desc(), RepairReservation.id.desc())
        )
        return list(result.all())

    async def exists_confirmed_slot(
        self,
        *,
        store_id: UUID,
        slot: datetime,
    ) -> bool:
        row = await self.session.scalar(
            select(RepairReservation.id).where(
                RepairReservation.store_id == store_id,
                RepairReservation.slot == slot,
                RepairReservation.status == RepairReservationStatus.CONFIRMED,
            )
        )
        return row is not None
