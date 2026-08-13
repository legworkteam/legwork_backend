from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import RepairReservationStatus


class RepairReservationCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    diagnosis_id: uuid.UUID = Field(alias="diagnosisId")
    store_id: uuid.UUID = Field(alias="storeId")
    slot: datetime
    note: str | None = Field(default=None, max_length=500)

    @field_validator("slot")
    @classmethod
    def validate_slot(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("slot must include timezone information.")
        return value


class RepairReservationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    repair_reservation_id: uuid.UUID = Field(alias="repairReservationId")
    diagnosis_id: uuid.UUID = Field(alias="diagnosisId")
    store_id: uuid.UUID = Field(alias="storeId")
    slot: datetime
    status: RepairReservationStatus
    note: str | None = None
    cancelled_at: datetime | None = Field(alias="cancelledAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
