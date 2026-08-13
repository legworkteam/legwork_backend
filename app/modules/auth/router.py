"""Auth endpoints: signup, login, refresh, logout."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)
from app.modules.auth.service import AuthService
from app.modules.users.repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(UserRepository(session), RefreshTokenRepository(session))


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/signup",
    response_model=ApiResponse[SignupResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Sign up (LOCAL)",
)
async def signup(
    request: Request, payload: SignupRequest, service: AuthServiceDep
) -> ApiResponse[SignupResponse]:
    data = await service.signup(payload)
    return success_response(data=data, request=request)


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="Log in (LOCAL)",
)
async def login(
    request: Request, payload: LoginRequest, service: AuthServiceDep
) -> ApiResponse[TokenResponse]:
    data = await service.login(payload)
    return success_response(data=data, request=request)


@router.post(
    "/refresh",
    response_model=ApiResponse[TokenResponse],
    summary="Refresh tokens (rotation)",
)
async def refresh(
    request: Request, payload: RefreshRequest, service: AuthServiceDep
) -> ApiResponse[TokenResponse]:
    data = await service.refresh(payload)
    return success_response(data=data, request=request)


@router.post(
    "/logout",
    response_model=ApiResponse[None],
    summary="Log out (revoke refresh token)",
)
async def logout(
    request: Request,
    payload: LogoutRequest,
    service: AuthServiceDep,
    _current_user: CurrentUser,
) -> ApiResponse[None]:
    await service.logout(payload.refresh_token)
    return success_response(data=None, request=request)
