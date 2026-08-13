"""Owned product (after-care) schemas (camelCase JSON)."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import RegisteredProductSource


class RegisterProductRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    serial_number: str = Field(alias="serialNumber", min_length=1, max_length=150)
    purchase_date: date | None = Field(default=None, alias="purchaseDate")
    nickname: str | None = Field(default=None, max_length=100)


class RegisteredProductItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    registration_id: uuid.UUID = Field(alias="registrationId")
    product_id: uuid.UUID = Field(alias="productId")
    product_code: str = Field(alias="productCode")
    name: str
    thumbnail_file_id: uuid.UUID | None = Field(default=None, alias="thumbnailFileId")
    source: RegisteredProductSource
    serial_number: str | None = Field(default=None, alias="serialNumber")
    nickname: str | None = None
    purchase_date: date | None = Field(default=None, alias="purchaseDate")
    created_at: datetime = Field(alias="createdAt")


class RegisteredProductDetail(RegisteredProductItem):
    category: str | None = None
    base_price: int = Field(alias="basePrice")
    currency: str


class CareGuideResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: uuid.UUID = Field(alias="productId")
    title: str
    guide: dict
    as_info: dict | None = Field(default=None, alias="asInfo")
    source: str  # "product" | "categoryDefault"
