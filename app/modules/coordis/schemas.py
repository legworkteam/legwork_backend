from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.modules.products.schemas import ProductSummary, VariantInfo


class SavedCoordiItemPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: uuid.UUID = Field(alias="productId")
    variant_id: uuid.UUID | None = Field(default=None, alias="variantId")


class SavedCoordiCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    items: list[SavedCoordiItemPayload]

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name is required.")
        return value

    @field_validator("items")
    @classmethod
    def validate_items(cls, value: list[SavedCoordiItemPayload]) -> list[SavedCoordiItemPayload]:
        if not value:
            raise ValueError("items must not be empty.")
        return value


class SavedCoordiUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    items: list[SavedCoordiItemPayload] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("name must not be empty.")
        return value

    @field_validator("items")
    @classmethod
    def validate_items(cls, value: list[SavedCoordiItemPayload] | None) -> list[SavedCoordiItemPayload] | None:
        if value is not None and not value:
            raise ValueError("items must not be empty.")
        return value


class SavedCoordiSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID = Field(alias="savedCoordiId")
    name: str
    thumbnail_file_id: uuid.UUID | None = Field(default=None, alias="thumbnailFileId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class SavedCoordiItemDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(alias="savedCoordiItemId")
    product_id: uuid.UUID = Field(alias="productId")
    variant_id: uuid.UUID | None = Field(default=None, alias="variantId")
    sort_order: int = Field(alias="sortOrder")
    product: ProductSummary
    variant: VariantInfo | None = None


class SavedCoordiDetail(SavedCoordiSummary):
    items: list[SavedCoordiItemDetail] = Field(default_factory=list)
