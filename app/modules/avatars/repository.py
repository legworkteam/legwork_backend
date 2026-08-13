from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.avatars.models import Avatar


class AvatarRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: uuid.UUID) -> Avatar | None:
        return await self.session.scalar(select(Avatar).where(Avatar.user_id == user_id))

    async def add(self, avatar: Avatar) -> Avatar:
        self.session.add(avatar)
        await self.session.flush()
        await self.session.refresh(avatar)
        return avatar

    async def delete(self, avatar: Avatar) -> None:
        await self.session.delete(avatar)
