from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.diagnoses.repository import DiagnosisRepository
from app.modules.repairs.repository import RepairReservationRepository
from app.modules.repairs.schemas import RepairReservationCreateRequest, RepairReservationSchema
from app.modules.repairs.service import RepairReservationService
from app.modules.stores.router import StoreServiceDep


router = APIRouter(tags=["repair-reservations"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_repair_reservation_service(
    session: DbSession,
    store_service: StoreServiceDep,
) -> RepairReservationService:
    return RepairReservationService(
        session,
        diagnosis_repository=DiagnosisRepository(session),
        store_service=store_service,
        repository=RepairReservationRepository(session),
    )


RepairReservationServiceDep = Annotated[
    RepairReservationService,
    Depends(get_repair_reservation_service),
]


@router.post(
    "/repair-reservations",
    response_model=ApiResponse[RepairReservationSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create repair reservation",
)
async def create_repair_reservation(
    request: Request,
    payload: RepairReservationCreateRequest,
    current_user: CurrentUser,
    service: RepairReservationServiceDep,
) -> ApiResponse[RepairReservationSchema]:
    data = await service.create(user_id=current_user.id, payload=payload)
    return success_response(data=data, request=request)


@router.get(
    "/repair-reservations",
    response_model=ApiResponse[list[RepairReservationSchema]],
    summary="List my repair reservations",
)
async def list_repair_reservations(
    request: Request,
    current_user: CurrentUser,
    service: RepairReservationServiceDep,
) -> ApiResponse[list[RepairReservationSchema]]:
    data = await service.list_owned(user_id=current_user.id)
    return success_response(data=data, request=request)


@router.post(
    "/repair-reservations/{repairReservationId}/cancel",
    response_model=ApiResponse[RepairReservationSchema],
    summary="Cancel repair reservation",
)
async def cancel_repair_reservation(
    repairReservationId: UUID,
    request: Request,
    current_user: CurrentUser,
    service: RepairReservationServiceDep,
) -> ApiResponse[RepairReservationSchema]:
    data = await service.cancel(
        user_id=current_user.id,
        reservation_id=repairReservationId,
    )
    return success_response(data=data, request=request)
