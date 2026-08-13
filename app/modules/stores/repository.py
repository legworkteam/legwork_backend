"""Persistence for stores (Backend A)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.stores.models import Store


class StoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active(self, limit: int) -> list[Store]:
        result = await self.session.scalars(
            select(Store).where(Store.active.is_(True)).order_by(Store.name).limit(limit)
        )
        return list(result)

    async def get_active_by_id(self, store_id) -> Store | None:
        return await self.session.scalar(
            select(Store).where(Store.id == store_id, Store.active.is_(True))
        )
