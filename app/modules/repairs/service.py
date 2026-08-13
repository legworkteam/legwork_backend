from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RepairReservationStatus
from app.core.exceptions import NotFoundError, RepairNotNeededError, ReservationSlotUnavailableError, ValidationError
from app.modules.diagnoses.repository import DiagnosisRepository
from app.modules.repairs.models import RepairReservation
from app.modules.repairs.repository import RepairReservationRepository
from app.modules.repairs.schemas import RepairReservationCreateRequest, RepairReservationSchema
from app.modules.stores.service import StoreService
from app.utils.datetime import now_kst


class RepairReservationNotFoundError(NotFoundError):
    code = "REPAIR_RESERVATION_NOT_FOUND"
    message = "Repair reservation not found."


class RepairReservationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        diagnosis_repository: DiagnosisRepository,
        store_service: StoreService,
        repository: RepairReservationRepository | None = None,
    ) -> None:
        self.session = session
        self.diagnoses = diagnosis_repository
        self.stores = store_service
        self.repository = repository or RepairReservationRepository(session)

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        payload: RepairReservationCreateRequest,
    ) -> RepairReservationSchema:
        diagnosis = await self.diagnoses.get_owned_by_id(
            diagnosis_id=payload.diagnosis_id,
            user_id=user_id,
        )
        if diagnosis is None:
            raise NotFoundError("Diagnosis not found.")
        if not diagnosis.repair_needed:
            raise RepairNotNeededError()
        await self.stores.ensure_active_store(payload.store_id)
        if await self.repository.exists_confirmed_slot(
            store_id=payload.store_id,
            slot=payload.slot,
        ):
            raise ReservationSlotUnavailableError()

        reservation = await self.repository.add(
            RepairReservation(
                diagnosis_id=payload.diagnosis_id,
                store_id=payload.store_id,
                slot=payload.slot,
                status=RepairReservationStatus.CONFIRMED,
                note=payload.note,
            )
        )
        await self.session.commit()
        return RepairReservationSchema.model_validate(
            {
                "repairReservationId": reservation.id,
                "diagnosisId": reservation.diagnosis_id,
                "storeId": reservation.store_id,
                "slot": reservation.slot,
                "status": reservation.status,
                "note": reservation.note,
                "cancelledAt": reservation.cancelled_at,
                "createdAt": reservation.created_at,
                "updatedAt": reservation.updated_at,
            }
        )

    async def list_owned(self, *, user_id: uuid.UUID) -> list[RepairReservationSchema]:
        rows = await self.repository.list_owned(user_id=user_id)
        return [
            RepairReservationSchema.model_validate(
                {
                    "repairReservationId": row.id,
                    "diagnosisId": row.diagnosis_id,
                    "storeId": row.store_id,
                    "slot": row.slot,
                    "status": row.status,
                    "note": row.note,
                    "cancelledAt": row.cancelled_at,
                    "createdAt": row.created_at,
                    "updatedAt": row.updated_at,
                }
            )
            for row in rows
        ]

    async def cancel(
        self,
        *,
        user_id: uuid.UUID,
        reservation_id: uuid.UUID,
    ) -> RepairReservationSchema:
        row = await self.repository.get_owned_by_id(
            reservation_id=reservation_id,
            user_id=user_id,
        )
        if row is None:
            raise RepairReservationNotFoundError()
        if row.status is not RepairReservationStatus.CONFIRMED:
            raise ValidationError("Only confirmed reservations can be cancelled.")

        row.status = RepairReservationStatus.CANCELLED
        row.cancelled_at = now_kst()
        row.updated_at = now_kst()
        await self.session.commit()
        await self.session.refresh(row)
        return RepairReservationSchema.model_validate(
            {
                "repairReservationId": row.id,
                "diagnosisId": row.diagnosis_id,
                "storeId": row.store_id,
                "slot": row.slot,
                "status": row.status,
                "note": row.note,
                "cancelledAt": row.cancelled_at,
                "createdAt": row.created_at,
                "updatedAt": row.updated_at,
            }
        )
