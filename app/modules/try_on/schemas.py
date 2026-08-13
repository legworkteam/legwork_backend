from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import Gender, TryOnScope


class AvatarParametersOverride(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    height_cm: float | None = Field(default=None, alias="heightCm")
    weight_kg: float | None = Field(default=None, alias="weightKg")
    gender: Gender | None = None

    @field_validator("height_cm")
    @classmethod
    def validate_height(cls, value: float | None) -> float | None:
        if value is not None and (value < 100 or value > 230):
            raise ValueError("heightCm must be between 100 and 230.")
        return value

    @field_validator("weight_kg")
    @classmethod
    def validate_weight(cls, value: float | None) -> float | None:
        if value is not None and (value < 30 or value > 200):
            raise ValueError("weightKg must be between 30 and 200.")
        return value


class AvatarTryOnRequest(AvatarParametersOverride):
    scope: TryOnScope
    product_id: uuid.UUID | None = Field(default=None, alias="productId")
    saved_coordi_id: uuid.UUID | None = Field(default=None, alias="savedCoordiId")
    variant_id: uuid.UUID | None = Field(default=None, alias="variantId")
    simulate_failure: bool = Field(default=False, alias="simulateFailure")


class PhotoTryOnRequest(AvatarParametersOverride):
    scope: TryOnScope
    product_id: uuid.UUID | None = Field(default=None, alias="productId")
    saved_coordi_id: uuid.UUID | None = Field(default=None, alias="savedCoordiId")
    variant_id: uuid.UUID | None = Field(default=None, alias="variantId")
    simulate_failure: bool = Field(default=False, alias="simulateFailure")


class TryOnJobAcceptedResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    job_id: uuid.UUID = Field(alias="jobId")


class TryOnSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID = Field(alias="tryOnId")
    job_id: uuid.UUID = Field(alias="jobId")
    user_id: uuid.UUID | None = Field(alias="userId")
    guest_session_id: uuid.UUID | None = Field(alias="guestSessionId")
    scope: TryOnScope
    product_id: uuid.UUID | None = Field(alias="productId")
    saved_coordi_id: uuid.UUID | None = Field(alias="savedCoordiId")
    result_file_id: uuid.UUID = Field(alias="resultFileId")
    provider: str
    saved_at: datetime | None = Field(alias="savedAt")
    expires_at: datetime | None = Field(alias="expiresAt")
    created_at: datetime = Field(alias="createdAt")
