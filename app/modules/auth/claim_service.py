"""Guest -> member claim (Backend A).

Migrates a guest session's permanent-izable data to the logged-in member.
Currently claims RecentProduct rows (fully A-owned). Avatar params, saved
try-ons and coordis are Backend B entities and will be claimed via B's
services once available.
"""

import uuid

import jwt

from app.core.exceptions import UnauthorizedError
from app.core.security import decode_token
from app.modules.auth.schemas import ClaimResponse
from app.modules.products.repository import RecentProductRepository


class ClaimService:
    def __init__(self, recent_repository: RecentProductRepository) -> None:
        self.recent = recent_repository

    def _guest_session_id(self, guest_token: str) -> uuid.UUID:
        try:
            payload = decode_token(guest_token)
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("유효하지 않은 게스트 토큰입니다.") from exc
        if payload.get("type") != "guest":
            raise UnauthorizedError("게스트 토큰이 아닙니다.")
        try:
            return uuid.UUID(payload["sub"])
        except (KeyError, ValueError) as exc:
            raise UnauthorizedError("유효하지 않은 게스트 토큰입니다.") from exc

    async def claim(self, user_id: uuid.UUID, guest_token: str) -> ClaimResponse:
        guest_session_id = self._guest_session_id(guest_token)
        rows = await self.recent.list_for_guest(guest_session_id)

        claimed = 0
        for row in rows:
            existing = await self.recent.get_for_owner(
                product_id=row.product_id, user_id=user_id, guest_session_id=None
            )
            if existing is not None:
                # member already saw this product: keep the latest view, drop the guest row
                if row.viewed_at > existing.viewed_at:
                    existing.viewed_at = row.viewed_at
                await self.recent.delete(row)
            else:
                row.user_id = user_id
                row.guest_session_id = None
            claimed += 1

        return ClaimResponse(recentProductsClaimed=claimed)
