"""Store business rules (Backend A).

Lists stores and demo reservation slots for a date. Actual slot-conflict
checks live in Backend B's repair flow; here A just surfaces candidate slots
from business hours so the frontend can render availability.
"""

from datetime import date, datetime, time

from app.core.exceptions import NotFoundError
from app.modules.stores.repository import StoreRepository
from app.modules.stores.schemas import StoreItem, StoreListResponse
from app.utils.datetime import KST, now_kst

# Demo business hours: hourly slots 11:00–18:00 KST.
_SLOT_HOURS = range(11, 19)


def _slots_for(target: date) -> list[datetime]:
    return [
        datetime.combine(target, time(hour=h), tzinfo=KST) for h in _SLOT_HOURS
    ]


class StoreService:
    def __init__(self, repository: StoreRepository) -> None:
        self.repository = repository

    async def list_stores(
        self, *, target_date: date | None, limit: int
    ) -> StoreListResponse:
        target = target_date or now_kst().date()
        slots = _slots_for(target)
        stores = await self.repository.list_active(limit)
        return StoreListResponse(
            stores=[
                StoreItem(
                    storeId=s.id,
                    name=s.name,
                    address=s.address,
                    phone=s.phone,
                    availableSlots=slots,
                )
                for s in stores
            ]
        )

    async def ensure_active_store(self, store_id) -> None:
        store = await self.repository.get_active_by_id(store_id)
        if store is None:
            raise NotFoundError("Store not found.")
