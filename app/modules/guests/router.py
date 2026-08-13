"""Guest session endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.guests.repository import GuestRepository
from app.modules.guests.schemas import GuestSessionCreateRequest, GuestSessionResponse
from app.modules.guests.service import GuestService

router = APIRouter(tags=["guests"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_guest_service(session: DbSession) -> GuestService:
    return GuestService(GuestRepository(session))


GuestServiceDep = Annotated[GuestService, Depends(get_guest_service)]


@router.post(
    "/guest-sessions",
    response_model=ApiResponse[GuestSessionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create guest session",
)
async def create_guest_session(
    request: Request,
    service: GuestServiceDep,
    payload: GuestSessionCreateRequest | None = None,
) -> ApiResponse[GuestSessionResponse]:
    data = await service.create_session(payload or GuestSessionCreateRequest())
    return success_response(data=data, request=request)
