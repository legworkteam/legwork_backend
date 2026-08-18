from __future__ import annotations

import uuid
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentPrincipal, CurrentUser, Principal
from app.api.dependencies.database import get_db_session
from app.core.config import settings
from app.core.enums import Gender, TryOnScope
from app.core.responses import ApiResponse, success_response
from app.modules.products.router import ProductServiceDep
from app.modules.try_on.repository import TryOnRepository
from app.modules.try_on.schemas import AvatarTryOnRequest, PhotoTryOnRequest, TryOnJobAcceptedResponse, TryOnSchema
from app.modules.try_on.service import TryOnService
from app.providers.try_on.base import TryOnProvider
from app.providers.try_on.mock import MockTryOnProvider
from app.providers.try_on.openai_edit import OpenAITryOnProvider
from app.storage.base import StorageService
from app.storage.local import LocalStorageService


router = APIRouter(tags=["try-on"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


@lru_cache
def get_try_on_provider() -> TryOnProvider:
    if settings.try_on_provider == "openai":
        return OpenAITryOnProvider()
    return MockTryOnProvider()


@lru_cache
def get_storage_service() -> StorageService:
    return LocalStorageService()


def get_try_on_service(
    session: DbSession,
    product_service: ProductServiceDep,
    provider: Annotated[TryOnProvider, Depends(get_try_on_provider)],
    storage: Annotated[StorageService, Depends(get_storage_service)],
) -> TryOnService:
    return TryOnService(
        session,
        product_service=product_service,
        provider=provider,
        storage=storage,
        try_on_repository=TryOnRepository(session),
    )


TryOnServiceDep = Annotated[TryOnService, Depends(get_try_on_service)]


def _parse_photo_payload(
    *,
    scope: TryOnScope,
    product_id: uuid.UUID | None,
    saved_coordi_id: uuid.UUID | None,
    variant_id: uuid.UUID | None,
    height_cm: float | None,
    weight_kg: float | None,
    gender: Gender | None,
    simulate_failure: bool,
) -> PhotoTryOnRequest:
    return PhotoTryOnRequest(
        scope=scope,
        productId=product_id,
        savedCoordiId=saved_coordi_id,
        variantId=variant_id,
        heightCm=height_cm,
        weightKg=weight_kg,
        gender=gender,
        simulateFailure=simulate_failure,
    )


@router.post(
    "/avatar-try-ons",
    response_model=ApiResponse[TryOnJobAcceptedResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create avatar try-on job",
)
async def create_avatar_try_on(
    request: Request,
    payload: AvatarTryOnRequest,
    principal: CurrentPrincipal,
    service: TryOnServiceDep,
    background_tasks: BackgroundTasks,
) -> ApiResponse[TryOnJobAcceptedResponse]:
    data = await service.enqueue_avatar_try_on(
        principal=principal,
        payload=payload,
        background_tasks=background_tasks,
    )
    return success_response(data=data, request=request)


@router.post(
    "/try-ons",
    response_model=ApiResponse[TryOnJobAcceptedResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create photo try-on job",
)
async def create_photo_try_on(
    request: Request,
    principal: CurrentPrincipal,
    service: TryOnServiceDep,
    background_tasks: BackgroundTasks,
    photo: UploadFile = File(...),
    scope: TryOnScope = Form(...),
    productId: uuid.UUID | None = Form(default=None),
    savedCoordiId: uuid.UUID | None = Form(default=None),
    variantId: uuid.UUID | None = Form(default=None),
    heightCm: float | None = Form(default=None),
    weightKg: float | None = Form(default=None),
    gender: Gender | None = Form(default=None),
    simulateFailure: bool = Form(default=False),
) -> ApiResponse[TryOnJobAcceptedResponse]:
    payload = _parse_photo_payload(
        scope=scope,
        product_id=productId,
        saved_coordi_id=savedCoordiId,
        variant_id=variantId,
        height_cm=heightCm,
        weight_kg=weightKg,
        gender=gender,
        simulate_failure=simulateFailure,
    )
    data = await service.enqueue_photo_try_on(
        principal=principal,
        payload=payload,
        photo=photo,
        background_tasks=background_tasks,
    )
    return success_response(data=data, request=request)


@router.post(
    "/try-ons/{tryOnId}/save",
    response_model=ApiResponse[TryOnSchema],
    summary="Save try-on result",
)
async def save_try_on(
    tryOnId: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    service: TryOnServiceDep,
) -> ApiResponse[TryOnSchema]:
    data = await service.save_try_on(
        try_on_id=tryOnId,
        principal=Principal(kind="member", user_id=current_user.id),
    )
    return success_response(data=data, request=request)


@router.get(
    "/me/try-ons",
    response_model=ApiResponse[list[TryOnSchema]],
    summary="List saved try-on results",
)
async def list_saved_try_ons(
    request: Request,
    current_user: CurrentUser,
    service: TryOnServiceDep,
) -> ApiResponse[list[TryOnSchema]]:
    data = await service.get_saved_try_ons(user_id=current_user.id)
    return success_response(data=data, request=request)


@router.delete(
    "/me/try-ons/{tryOnId}",
    response_model=ApiResponse[dict],
    summary="Delete saved try-on result",
)
async def delete_saved_try_on(
    tryOnId: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    service: TryOnServiceDep,
) -> ApiResponse[dict]:
    await service.delete_saved_try_on(
        try_on_id=tryOnId,
        principal=Principal(kind="member", user_id=current_user.id),
    )
    return success_response(data={"deleted": True}, request=request)
