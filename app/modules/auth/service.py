"""Auth business rules: signup, login (with lockout), refresh (rotation), logout.

Only LOCAL accounts are handled here; social login is a separate flow. Refresh
tokens are opaque, stored as SHA-256 hashes, and rotated on every refresh.
"""

from datetime import timedelta

from fastapi import status

from app.core.config import settings
from app.core.enums import AuthProvider
from app.core.exceptions import AppException, ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    refresh_token_expiry,
    verify_password,
)
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
)
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.utils.datetime import now_kst

MAX_LOGIN_FAILURES = 5
LOCK_DURATION = timedelta(minutes=15)


class EmailAlreadyExistsError(ConflictError):
    code = "EMAIL_ALREADY_EXISTS"
    message = "이미 사용 중인 이메일입니다."


class InvalidCredentialsError(UnauthorizedError):
    message = "이메일 또는 비밀번호가 올바르지 않습니다."


class LoginLockedError(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    code = "LOGIN_TEMPORARILY_LOCKED"
    message = "로그인 시도가 일시적으로 잠겼습니다. 잠시 후 다시 시도해주세요."


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
        token_repository: RefreshTokenRepository,
    ) -> None:
        self.users = user_repository
        self.tokens = token_repository

    async def signup(self, payload: SignupRequest) -> SignupResponse:
        existing = await self.users.get_active_local_by_email(payload.email)
        if existing is not None:
            raise EmailAlreadyExistsError()

        user = User(
            name=payload.name,
            email=payload.email,
            auth_provider=AuthProvider.LOCAL,
            password_hash=hash_password(payload.password),
            phone=payload.phone,
        )
        await self.users.add(user)
        return SignupResponse(userId=user.id)

    async def login(self, payload: LoginRequest) -> TokenResponse:
        user = await self.users.get_active_local_by_email(payload.email)
        if user is None or user.password_hash is None:
            raise InvalidCredentialsError()

        now = now_kst()
        if user.locked_until is not None and user.locked_until > now:
            raise LoginLockedError()

        if not verify_password(payload.password, user.password_hash):
            user.login_fail_count += 1
            if user.login_fail_count >= MAX_LOGIN_FAILURES:
                user.locked_until = now + LOCK_DURATION
                user.login_fail_count = 0
                raise LoginLockedError()
            raise InvalidCredentialsError()

        # success: reset counters, issue tokens
        user.login_fail_count = 0
        user.locked_until = None
        return await self._issue_tokens(user)

    async def refresh(self, payload: RefreshRequest) -> TokenResponse:
        token_hash = hash_refresh_token(payload.refresh_token)
        record = await self.tokens.get_active_by_hash(token_hash)
        if record is None or record.expires_at <= now_kst():
            raise UnauthorizedError("유효하지 않은 refresh token입니다.")

        # rotation: revoke the presented token, issue a fresh pair
        record.revoked_at = now_kst()
        user = await self.users.get_active_by_id(record.user_id)
        if user is None:
            raise UnauthorizedError("사용자를 찾을 수 없습니다.")
        return await self._issue_tokens(user)

    async def logout(self, refresh_token: str) -> None:
        record = await self.tokens.get_active_by_hash(hash_refresh_token(refresh_token))
        if record is not None:
            record.revoked_at = now_kst()

    async def _issue_tokens(self, user: User) -> TokenResponse:
        access_token = create_access_token(str(user.id))
        raw_refresh = generate_refresh_token()
        expires_at = refresh_token_expiry()
        await self.tokens.add(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=expires_at,
        )
        return TokenResponse(
            userId=user.id,
            accessToken=access_token,
            refreshToken=raw_refresh,
            accessTokenExpiresIn=settings.access_token_expire_minutes * 60,
            refreshTokenExpiresIn=settings.refresh_token_expire_days * 86400,
        )
