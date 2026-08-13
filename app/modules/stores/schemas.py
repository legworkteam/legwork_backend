"""Store request/response schemas (camelCase JSON)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StoreItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    store_id: uuid.UUID = Field(alias="storeId")
    name: str
    address: str | None = None
    phone: str | None = None
    available_slots: list[datetime] = Field(default_factory=list, alias="availableSlots")


class StoreListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stores: list[StoreItem] = Field(default_factory=list)
