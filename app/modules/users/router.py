"""Member account endpoints (MEMBER)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.avatars.repository import AvatarRepository
from app.modules.users.schemas import (
    ChangePasswordRequest,
    MeResponse,
    UpdateMeRequest,
)
from app.modules.users.service import UserService

router = APIRouter(tags=["users"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_user_service() -> UserService:
    return UserService()


UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.get("/me", response_model=ApiResponse[MeResponse], summary="Get my profile")
async def get_me(
    request: Request,
    user: CurrentUser,
    service: UserServiceDep,
    session: DbSession,
) -> ApiResponse[MeResponse]:
    has_avatar = await AvatarRepository(session).get_by_user_id(user.id) is not None
    return success_response(data=service.get_me(user, has_avatar=has_avatar), request=request)


@router.patch("/me", response_model=ApiResponse[MeResponse], summary="Update my profile")
async def update_me(
    request: Request,
    payload: UpdateMeRequest,
    user: CurrentUser,
    service: UserServiceDep,
) -> ApiResponse[MeResponse]:
    return success_response(data=service.update_me(user, payload), request=request)


@router.patch(
    "/me/password",
    response_model=ApiResponse[None],
    summary="Change my password",
)
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    user: CurrentUser,
    service: UserServiceDep,
) -> ApiResponse[None]:
    service.change_password(user, payload)
    return success_response(data=None, request=request)
