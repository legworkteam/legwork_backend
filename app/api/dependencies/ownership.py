from dataclasses import dataclass
from uuid import UUID

from fastapi import Header

from app.core.enums import PrincipalType
from app.core.exceptions import ForbiddenError, UnauthorizedError


@dataclass(frozen=True)
class Principal:
    type: PrincipalType
    owner_id: UUID


def _parse_authorization_header(authorization: str | None) -> Principal:
    if not authorization:
        raise UnauthorizedError("Authorization header is required.")

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise UnauthorizedError("Bearer token is required.")

    principal_type, _, raw_id = token.partition(":")
    if principal_type not in {PrincipalType.USER.value, PrincipalType.GUEST.value} or not raw_id:
        raise UnauthorizedError("Unsupported token format.")

    try:
        owner_id = UUID(raw_id)
    except ValueError as exc:
        raise UnauthorizedError("Invalid token subject.") from exc

    return Principal(type=PrincipalType(principal_type), owner_id=owner_id)


async def get_guest_or_member_principal(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> Principal:
    # TODO(Backend A): replace this temporary parser with real guest token/JWT verification.
    return _parse_authorization_header(authorization)


def ensure_file_access(principal: Principal, *, owner_type: str, owner_id: UUID | None) -> None:
    if owner_id is None:
        raise ForbiddenError("Owner is not assigned to this file.")

    if principal.type.value != owner_type or principal.owner_id != owner_id:
        raise ForbiddenError("You do not own this file.")


def ensure_job_access(
    principal: Principal,
    *,
    user_id: UUID | None,
    guest_session_id: UUID | None,
) -> None:
    if principal.type is PrincipalType.USER and user_id == principal.owner_id:
        return
    if principal.type is PrincipalType.GUEST and guest_session_id == principal.owner_id:
        return
    raise ForbiddenError("You do not own this job.")
