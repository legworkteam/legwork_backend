from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.coordis.repository import SavedCoordiRepository
from app.modules.coordis.schemas import (
    SavedCoordiCreateRequest,
    SavedCoordiDetail,
    SavedCoordiSummary,
    SavedCoordiUpdateRequest,
)
from app.modules.coordis.service import SavedCoordiService
from app.modules.products.router import ProductServiceDep


router = APIRouter(tags=["coordis"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_saved_coordi_service(
    session: DbSession,
    product_service: ProductServiceDep,
) -> SavedCoordiService:
    return SavedCoordiService(SavedCoordiRepository(session), product_service=product_service)


SavedCoordiServiceDep = Annotated[SavedCoordiService, Depends(get_saved_coordi_service)]


@router.post(
    "/me/coordis",
    response_model=ApiResponse[SavedCoordiDetail],
    status_code=status.HTTP_201_CREATED,
    summary="Create saved coordi",
)
async def create_saved_coordi(
    request: Request,
    payload: SavedCoordiCreateRequest,
    current_user: CurrentUser,
    service: SavedCoordiServiceDep,
) -> ApiResponse[SavedCoordiDetail]:
    data = await service.create(user_id=current_user.id, payload=payload)
    return success_response(data=data, request=request)


@router.get(
    "/me/coordis",
    response_model=ApiResponse[list[SavedCoordiSummary]],
    summary="List saved coordis",
)
async def list_saved_coordis(
    request: Request,
    current_user: CurrentUser,
    service: SavedCoordiServiceDep,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
) -> ApiResponse[list[SavedCoordiSummary]]:
    data, pagination = await service.list_owned(
        user_id=current_user.id,
        cursor=cursor,
        limit=limit,
    )
    return success_response(data=data, request=request, pagination=pagination)


@router.get(
    "/me/coordis/{savedCoordiId}",
    response_model=ApiResponse[SavedCoordiDetail],
    summary="Get saved coordi detail",
)
async def get_saved_coordi(
    savedCoordiId: UUID,
    request: Request,
    current_user: CurrentUser,
    service: SavedCoordiServiceDep,
) -> ApiResponse[SavedCoordiDetail]:
    data = await service.get_owned(saved_coordi_id=savedCoordiId, user_id=current_user.id)
    return success_response(data=data, request=request)


@router.patch(
    "/me/coordis/{savedCoordiId}",
    response_model=ApiResponse[SavedCoordiDetail],
    summary="Update saved coordi",
)
async def update_saved_coordi(
    savedCoordiId: UUID,
    request: Request,
    payload: SavedCoordiUpdateRequest,
    current_user: CurrentUser,
    service: SavedCoordiServiceDep,
) -> ApiResponse[SavedCoordiDetail]:
    data = await service.update(
        saved_coordi_id=savedCoordiId,
        user_id=current_user.id,
        payload=payload,
    )
    return success_response(data=data, request=request)


@router.delete(
    "/me/coordis/{savedCoordiId}",
    response_model=ApiResponse[dict],
    summary="Delete saved coordi",
)
async def delete_saved_coordi(
    savedCoordiId: UUID,
    request: Request,
    current_user: CurrentUser,
    service: SavedCoordiServiceDep,
) -> ApiResponse[dict]:
    await service.delete(saved_coordi_id=savedCoordiId, user_id=current_user.id)
    return success_response(data={"deleted": True}, request=request)
