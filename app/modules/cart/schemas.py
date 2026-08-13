"""Cart request/response schemas (camelCase JSON)."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class AddCartItemRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    variant_id: uuid.UUID = Field(alias="variantId")
    quantity: int = Field(default=1, ge=1)


class UpdateCartItemRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    quantity: int | None = Field(default=None, ge=1)
    variant_id: uuid.UUID | None = Field(default=None, alias="variantId")


class CartItemResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cart_item_id: uuid.UUID = Field(alias="cartItemId")
    product_id: uuid.UUID = Field(alias="productId")
    product_code: str = Field(alias="productCode")
    name: str
    thumbnail_file_id: uuid.UUID | None = Field(default=None, alias="thumbnailFileId")
    variant_id: uuid.UUID = Field(alias="variantId")
    sku: str
    color: str | None = None
    size: str | None = None
    unit_price: int = Field(alias="unitPrice")
    quantity: int
    line_amount: int = Field(alias="lineAmount")
    stock: int


class CartResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    items: list[CartItemResponse] = Field(default_factory=list)
    total_amount: int = Field(alias="totalAmount")
    currency: str = "KRW"
