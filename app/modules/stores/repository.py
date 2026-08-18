"""Persistence for stores (Backend A)."""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RepairReservationStatus
from app.modules.repairs.models import RepairReservation
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

    async def list_confirmed_slots(
        self,
        store_ids: list[uuid.UUID],
        *,
        range_start: datetime,
        range_end: datetime,
    ) -> dict[uuid.UUID, set[datetime]]:
        """storeId -> confirmed reservation slots within [range_start, range_end)."""
        if not store_ids:
            return {}
        rows = await self.session.execute(
            select(RepairReservation.store_id, RepairReservation.slot).where(
                RepairReservation.store_id.in_(store_ids),
                RepairReservation.status == RepairReservationStatus.CONFIRMED,
                RepairReservation.slot >= range_start,
                RepairReservation.slot < range_end,
            )
        )
        booked: dict[uuid.UUID, set[datetime]] = {}
        for store_id, slot in rows.all():
            booked.setdefault(store_id, set()).add(slot)
        return booked
