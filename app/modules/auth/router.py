"""Auth endpoints: signup, login, refresh, logout."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import CurrentUser
from app.api.dependencies.database import get_db_session
from app.core.responses import ApiResponse, success_response
from app.modules.auth.claim_service import ClaimService
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.auth.schemas import (
    ClaimRequest,
    ClaimResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    SignupResponse,
    SocialLoginRequest,
    TokenResponse,
)
from app.modules.auth.service import AuthService
from app.modules.products.repository import RecentProductRepository
from app.modules.users.repository import UserRepository

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_auth_service(session: DbSession) -> AuthService:
    return AuthService(UserRepository(session), RefreshTokenRepository(session))


def get_claim_service(session: DbSession) -> ClaimService:
    return ClaimService(RecentProductRepository(session))


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ClaimServiceDep = Annotated[ClaimService, Depends(get_claim_service)]


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
    "/social",
    response_model=ApiResponse[TokenResponse],
    summary="Log in with Google/Kakao",
)
async def social_login(
    request: Request, payload: SocialLoginRequest, service: AuthServiceDep
) -> ApiResponse[TokenResponse]:
    data = await service.social_login(payload)
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


@router.post(
    "/claim",
    response_model=ApiResponse[ClaimResponse],
    summary="Claim guest data into the logged-in member",
)
async def claim(
    request: Request,
    payload: ClaimRequest,
    user: CurrentUser,
    service: ClaimServiceDep,
) -> ApiResponse[ClaimResponse]:
    data = await service.claim(user.id, payload.guest_token)
    return success_response(data=data, request=request)
