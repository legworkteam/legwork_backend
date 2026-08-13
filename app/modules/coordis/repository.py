from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.coordis.models import SavedCoordi, SavedCoordiItem


class SavedCoordiRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, row: SavedCoordi) -> SavedCoordi:
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        return row

    async def add_items(self, rows: list[SavedCoordiItem]) -> list[SavedCoordiItem]:
        self.session.add_all(rows)
        await self.session.flush()
        for row in rows:
            await self.session.refresh(row)
        return rows

    async def get_owned(self, *, saved_coordi_id: uuid.UUID, user_id: uuid.UUID) -> SavedCoordi | None:
        return await self.session.scalar(
            select(SavedCoordi).where(
                SavedCoordi.id == saved_coordi_id,
                SavedCoordi.user_id == user_id,
                SavedCoordi.deleted_at.is_(None),
            )
        )

    async def list_page(
        self,
        *,
        user_id: uuid.UUID,
        limit: int,
        cursor_created_at: datetime | None = None,
        cursor_id: uuid.UUID | None = None,
    ) -> list[SavedCoordi]:
        stmt = select(SavedCoordi).where(
            SavedCoordi.user_id == user_id,
            SavedCoordi.deleted_at.is_(None),
        )
        if cursor_created_at is not None and cursor_id is not None:
            stmt = stmt.where(
                or_(
                    SavedCoordi.created_at < cursor_created_at,
                    and_(
                        SavedCoordi.created_at == cursor_created_at,
                        SavedCoordi.id < cursor_id,
                    ),
                )
            )
        stmt = stmt.order_by(SavedCoordi.created_at.desc(), SavedCoordi.id.desc()).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def list_items(self, saved_coordi_id: uuid.UUID) -> list[SavedCoordiItem]:
        result = await self.session.scalars(
            select(SavedCoordiItem)
            .where(SavedCoordiItem.saved_coordi_id == saved_coordi_id)
            .order_by(SavedCoordiItem.sort_order.asc(), SavedCoordiItem.id.asc())
        )
        return list(result.all())

    async def replace_items(
        self,
        *,
        saved_coordi_id: uuid.UUID,
        rows: list[SavedCoordiItem],
    ) -> list[SavedCoordiItem]:
        await self.session.execute(
            delete(SavedCoordiItem).where(SavedCoordiItem.saved_coordi_id == saved_coordi_id)
        )
        if rows:
            await self.add_items(rows)
        return rows
