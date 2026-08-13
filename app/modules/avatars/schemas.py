from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import Gender


class AvatarParametersPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    height_cm: float = Field(alias="heightCm")
    weight_kg: float = Field(alias="weightKg")
    gender: Gender

    @field_validator("height_cm")
    @classmethod
    def validate_height(cls, value: float) -> float:
        if value < 100 or value > 230:
            raise ValueError("heightCm must be between 100 and 230.")
        return value

    @field_validator("weight_kg")
    @classmethod
    def validate_weight(cls, value: float) -> float:
        if value < 30 or value > 200:
            raise ValueError("weightKg must be between 30 and 200.")
        return value


class AvatarSchema(AvatarParametersPayload):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID = Field(alias="userId")
    preview_file_id: uuid.UUID | None = Field(default=None, alias="previewFileId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class GuestAvatarParametersSchema(AvatarParametersPayload):
    pass
