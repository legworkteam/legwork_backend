"""Order request/response schemas (camelCase JSON)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import OrderStatus, PaymentStatus


class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cart_item_ids: list[uuid.UUID] = Field(alias="cartItemIds", min_length=1)
    payment_method: str = Field(default="mock", alias="paymentMethod")


class CreateOrderResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_id: uuid.UUID = Field(alias="orderId")
    order_status: OrderStatus = Field(alias="orderStatus")
    payment_status: PaymentStatus = Field(alias="paymentStatus")
    paid_amount: int | None = Field(default=None, alias="paidAmount")
    paid_at: datetime | None = Field(default=None, alias="paidAt")


class OrderItemDetail(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: uuid.UUID = Field(alias="productId")
    variant_id: uuid.UUID = Field(alias="variantId")
    product_name: str = Field(alias="productName")
    variant: dict
    unit_price: int = Field(alias="unitPrice")
    quantity: int
    line_amount: int = Field(alias="lineAmount")


class OrderSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_id: uuid.UUID = Field(alias="orderId")
    order_status: OrderStatus = Field(alias="orderStatus")
    total_amount: int = Field(alias="totalAmount")
    currency: str
    paid_at: datetime | None = Field(default=None, alias="paidAt")
    created_at: datetime = Field(alias="createdAt")


class OrderDetail(OrderSummary):
    payment_status: PaymentStatus | None = Field(default=None, alias="paymentStatus")
    items: list[OrderItemDetail] = Field(default_factory=list)
