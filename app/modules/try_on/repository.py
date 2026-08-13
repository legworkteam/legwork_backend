from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.try_on.models import TryOn


class TryOnRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, try_on: TryOn) -> TryOn:
        self.session.add(try_on)
        await self.session.flush()
        await self.session.refresh(try_on)
        return try_on

    async def get_by_id(self, try_on_id: UUID) -> TryOn | None:
        return await self.session.get(TryOn, try_on_id)

    async def list_saved_by_user(self, user_id: UUID) -> list[TryOn]:
        result = await self.session.scalars(
            select(TryOn)
            .where(TryOn.user_id == user_id, TryOn.saved_at.is_not(None))
            .order_by(TryOn.saved_at.desc(), TryOn.created_at.desc())
        )
        return list(result.all())

    async def delete(self, try_on: TryOn) -> None:
        await self.session.delete(try_on)

    async def delete_expired_guest_rows(self, guest_session_id: UUID) -> None:
        await self.session.execute(
            delete(TryOn).where(TryOn.guest_session_id == guest_session_id, TryOn.expires_at.is_not(None))
        )
