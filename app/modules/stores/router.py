"""Store endpoints (MEMBER)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.stores.repository import StoreRepository
from app.modules.stores.schemas import StoreListResponse
from app.modules.stores.service import StoreService

router = APIRouter(tags=["stores"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_store_service(session: DbSession) -> StoreService:
    return StoreService(StoreRepository(session))


StoreServiceDep = Annotated[StoreService, Depends(get_store_service)]


@router.get(
    "/stores",
    response_model=ApiResponse[StoreListResponse],
    summary="List stores and reservation slots",
)
async def list_stores(
    request: Request,
    user: CurrentUser,
    service: StoreServiceDep,
    date_: date | None = Query(default=None, alias="date"),
    limit: int = Query(default=20, ge=1, le=50),
) -> ApiResponse[StoreListResponse]:
    data = await service.list_stores(target_date=date_, limit=limit)
    return success_response(data=data, request=request)
