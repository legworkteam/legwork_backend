"""Product DTOs (camelCase JSON).

These are the public contract of ProductService. Other domains (e.g. Backend B's
OCR) consume these schemas rather than importing A's ORM models.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductSummary(BaseModel):
    """Compact product info — matches the OCR recognition `product` block."""

    model_config = ConfigDict(populate_by_name=True)

    product_id: uuid.UUID = Field(alias="productId")
    product_code: str = Field(alias="productCode")
    name: str
    thumbnail_file_id: uuid.UUID | None = Field(default=None, alias="thumbnailFileId")
    base_price: int = Field(alias="basePrice")
    currency: str


class VariantInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    variant_id: uuid.UUID = Field(alias="variantId")
    sku: str
    color: str | None = None
    size: str | None = None
    price: int
    stock: int


class ProductImageInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    file_id: uuid.UUID = Field(alias="fileId")
    type: str | None = None
    sort_order: int = Field(alias="sortOrder")


class ProductTagInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tag_type: str = Field(alias="tagType")
    tag_value: str = Field(alias="tagValue")


class ProductDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: uuid.UUID = Field(alias="productId")
    product_code: str = Field(alias="productCode")
    name: str
    description: str | None = None
    category: str | None = None
    base_price: int = Field(alias="basePrice")
    currency: str
    thumbnail_file_id: uuid.UUID | None = Field(default=None, alias="thumbnailFileId")
    images: list[ProductImageInfo] = Field(default_factory=list)
    tags: list[ProductTagInfo] = Field(default_factory=list)
    variants: list[VariantInfo] = Field(default_factory=list)


class RecentProductItem(BaseModel):
    """A recently viewed product (summary + when it was last viewed)."""

    model_config = ConfigDict(populate_by_name=True)

    product_id: uuid.UUID = Field(alias="productId")
    product_code: str = Field(alias="productCode")
    name: str
    thumbnail_file_id: uuid.UUID | None = Field(default=None, alias="thumbnailFileId")
    base_price: int = Field(alias="basePrice")
    currency: str
    viewed_at: datetime = Field(alias="viewedAt")
