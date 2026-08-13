"""Authentication dependencies.

Resolves the request principal from a Bearer token:
- MEMBER endpoints use `get_current_user` (member JWT required).
- GUEST endpoints use `get_principal` (guest token OR member JWT).

Token decoding lives in core.security; here we validate type, load the owner
row, and map failures to domain exceptions.
"""

import uuid
from dataclasses import dataclass
from typing import Annotated, Literal

import jwt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db_session
from app.core.exceptions import (
    GuestSessionExpiredError,
    TokenExpiredError,
    UnauthorizedError,
)
from app.core.security import decode_token
from app.modules.guests.models import GuestSession
from app.modules.users.models import User
from app.utils.datetime import now_kst


@dataclass(frozen=True)
class Principal:
    kind: Literal["member", "guest"]
    user_id: uuid.UUID | None = None
    guest_session_id: uuid.UUID | None = None


def _bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("인증 토큰이 필요합니다.")
    return token


def _decode(token: str) -> dict:
    try:
        return decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError() from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("유효하지 않은 토큰입니다.") from exc


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user(request: Request, session: DbSession) -> User:
    """MEMBER: require a valid member JWT and return the active User."""
    payload = _decode(_bearer_token(request))
    if payload.get("type") != "access":
        raise UnauthorizedError("회원 인증이 필요합니다.")
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("유효하지 않은 토큰입니다.") from exc

    user = await session.scalar(
        select(User).where(User.id == user_id, User.deleted_at.is_(None))
    )
    if user is None:
        raise UnauthorizedError("사용자를 찾을 수 없습니다.")
    return user


async def get_principal(request: Request, session: DbSession) -> Principal:
    """GUEST: accept a member JWT or a non-expired guest token."""
    payload = _decode(_bearer_token(request))
    token_type = payload.get("type")

    if token_type == "access":
        try:
            user_id = uuid.UUID(payload["sub"])
        except (KeyError, ValueError) as exc:
            raise UnauthorizedError("유효하지 않은 토큰입니다.") from exc
        user = await session.scalar(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        if user is None:
            raise UnauthorizedError("사용자를 찾을 수 없습니다.")
        return Principal(kind="member", user_id=user.id)

    if token_type == "guest":
        try:
            guest_session_id = uuid.UUID(payload["sub"])
        except (KeyError, ValueError) as exc:
            raise UnauthorizedError("유효하지 않은 토큰입니다.") from exc
        guest = await session.get(GuestSession, guest_session_id)
        if guest is None:
            raise UnauthorizedError("게스트 세션을 찾을 수 없습니다.")
        if guest.expires_at <= now_kst():
            raise GuestSessionExpiredError()
        return Principal(kind="guest", guest_session_id=guest.id)

    raise UnauthorizedError("유효하지 않은 토큰입니다.")


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentPrincipal = Annotated[Principal, Depends(get_principal)]
