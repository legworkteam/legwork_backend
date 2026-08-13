"""Member account business rules: profile read/update, password change."""

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import hash_password, password_meets_policy, verify_password
from app.modules.users.models import User
from app.modules.users.schemas import (
    ChangePasswordRequest,
    MeResponse,
    UpdateMeRequest,
)


class PasswordAuthNotAvailableError(ConflictError):
    code = "PASSWORD_AUTH_NOT_AVAILABLE"
    message = "소셜 로그인 계정은 비밀번호를 변경할 수 없습니다."


class UserService:
    def __init__(self) -> None:
        # Profile ops act on the already-loaded, request-scoped User row, so no
        # repository is needed; the session flush/commit is owned by the dep.
        pass

    def get_me(self, user: User, *, has_avatar: bool = False) -> MeResponse:
        return MeResponse(
            userId=user.id,
            name=user.name,
            email=user.email,
            phone=user.phone,
            authProvider=user.auth_provider,
            hasAvatar=has_avatar,
            createdAt=user.created_at,
        )

    def update_me(self, user: User, payload: UpdateMeRequest) -> MeResponse:
        if payload.name is not None:
            user.name = payload.name
        if payload.phone is not None:
            user.phone = payload.phone
        return self.get_me(user)

    def change_password(self, user: User, payload: ChangePasswordRequest) -> None:
        if user.password_hash is None:
            # Social-only account has no local password to change.
            raise PasswordAuthNotAvailableError()
        if not verify_password(payload.current_password, user.password_hash):
            raise UnauthorizedError("현재 비밀번호가 올바르지 않습니다.")
        if not password_meets_policy(payload.new_password):
            # Defensive: schema already validates, but keep the rule at the boundary.
            raise UnauthorizedError("새 비밀번호가 정책을 만족하지 않습니다.")
        user.password_hash = hash_password(payload.new_password)
