from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentPrincipal, CurrentUser
from app.core.exceptions import ForbiddenError
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.avatars.repository import AvatarRepository
from app.modules.avatars.schemas import AvatarParametersPayload, AvatarSchema, GuestAvatarParametersSchema
from app.modules.avatars.service import AvatarService
from app.modules.guests.repository import GuestRepository


router = APIRouter(tags=["avatars"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_avatar_service(session: DbSession) -> AvatarService:
    return AvatarService(
        AvatarRepository(session),
        guest_repository=GuestRepository(session),
    )


AvatarServiceDep = Annotated[AvatarService, Depends(get_avatar_service)]


@router.post(
    "/me/avatar",
    response_model=ApiResponse[AvatarSchema],
    status_code=status.HTTP_201_CREATED,
    summary="Create member avatar",
)
async def create_avatar(
    request: Request,
    payload: AvatarParametersPayload,
    current_user: CurrentUser,
    service: AvatarServiceDep,
) -> ApiResponse[AvatarSchema]:
    data = await service.create_member_avatar(user_id=current_user.id, payload=payload)
    return success_response(data=data, request=request)


@router.get(
    "/me/avatar",
    response_model=ApiResponse[AvatarSchema],
    summary="Get member avatar",
)
async def get_avatar(
    request: Request,
    current_user: CurrentUser,
    service: AvatarServiceDep,
) -> ApiResponse[AvatarSchema]:
    data = await service.get_member_avatar(user_id=current_user.id)
    return success_response(data=data, request=request)


@router.put(
    "/me/avatar",
    response_model=ApiResponse[AvatarSchema],
    summary="Create or update member avatar",
)
async def update_avatar(
    request: Request,
    payload: AvatarParametersPayload,
    current_user: CurrentUser,
    service: AvatarServiceDep,
) -> ApiResponse[AvatarSchema]:
    data = await service.upsert_member_avatar(user_id=current_user.id, payload=payload)
    return success_response(data=data, request=request)


@router.put(
    "/guest-sessions/me/avatar-parameters",
    response_model=ApiResponse[GuestAvatarParametersSchema],
    summary="Update guest avatar parameters",
)
async def update_guest_avatar_parameters(
    request: Request,
    payload: AvatarParametersPayload,
    principal: CurrentPrincipal,
    service: AvatarServiceDep,
) -> ApiResponse[GuestAvatarParametersSchema]:
    if principal.guest_session_id is None:
        raise ForbiddenError("Guest session is required.")
    data = await service.update_guest_avatar_parameters(
        guest_session_id=principal.guest_session_id,
        payload=payload,
    )
    return success_response(data=data, request=request)
