from __future__ import annotations

from functools import lru_cache
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.diagnoses.schemas import (
    DiagnosisCareGuideResponse,
    DiagnosisDetailSchema,
    DiagnosisJobAcceptedResponse,
)
from app.modules.diagnoses.service import DiagnosisService
from app.modules.files.repository import FileRepository
from app.modules.owned_products.router import OwnedServiceDep, get_owned_product_service
from app.providers.diagnosis.base import DiagnosisProvider
from app.providers.diagnosis.mock import MockDiagnosisProvider
from app.storage.base import StorageService
from app.storage.local import LocalStorageService


router = APIRouter(tags=["diagnoses"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@lru_cache
def get_diagnosis_provider() -> DiagnosisProvider:
    return MockDiagnosisProvider()


@lru_cache
def get_storage_service() -> StorageService:
    return LocalStorageService()


def get_diagnosis_service(
    session: DbSession,
    owned_product_service: OwnedServiceDep,
    provider: Annotated[DiagnosisProvider, Depends(get_diagnosis_provider)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> DiagnosisService:
    return DiagnosisService(
        session,
        owned_product_service=owned_product_service,
        provider=provider,
        storage=storage,
        file_repository=FileRepository(session),
    )


DiagnosisServiceDep = Annotated[DiagnosisService, Depends(get_diagnosis_service)]


@router.post(
    "/diagnoses",
    response_model=ApiResponse[DiagnosisJobAcceptedResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create diagnosis job",
)
async def create_diagnosis(
    request: Request,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
    service: DiagnosisServiceDep,
    registeredProductId: UUID = Form(...),
    simulateFailure: bool = Form(default=False),
    image: UploadFile = File(...),
) -> ApiResponse[DiagnosisJobAcceptedResponse]:
    data = await service.enqueue_diagnosis(
        user_id=current_user.id,
        registered_product_id=registeredProductId,
        image=image,
        background_tasks=background_tasks,
        simulate_failure=simulateFailure,
    )
    return success_response(data=data, request=request)


@router.get(
    "/diagnoses/{diagnosisId}",
    response_model=ApiResponse[DiagnosisDetailSchema],
    summary="Get diagnosis detail",
)
async def get_diagnosis(
    diagnosisId: UUID,
    request: Request,
    current_user: CurrentUser,
    service: DiagnosisServiceDep,
) -> ApiResponse[DiagnosisDetailSchema]:
    data = await service.get_diagnosis(user_id=current_user.id, diagnosis_id=diagnosisId)
    return success_response(data=data, request=request)


@router.get(
    "/diagnoses/{diagnosisId}/care-guide",
    response_model=ApiResponse[DiagnosisCareGuideResponse],
    summary="Get care guide for diagnosis",
)
async def get_diagnosis_care_guide(
    diagnosisId: UUID,
    request: Request,
    current_user: CurrentUser,
    service: DiagnosisServiceDep,
) -> ApiResponse[DiagnosisCareGuideResponse]:
    data = await service.get_care_guide(user_id=current_user.id, diagnosis_id=diagnosisId)
    return success_response(data=data, request=request)
