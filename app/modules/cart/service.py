"""Cart business rules (member-only).

Validates variant availability/stock against the live product catalog. Re-adding
the same variant increases quantity. All prices are recomputed from the current
ProductVariant, never trusted from the client.
"""

import uuid

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.cart.repository import CartRepository
from app.modules.cart.schemas import (
    AddCartItemRequest,
    CartItemResponse,
    CartResponse,
    UpdateCartItemRequest,
)
from app.modules.products.models import ProductVariant
from app.modules.products.repository import ProductRepository


class VariantNotFoundError(NotFoundError):
    code = "VARIANT_NOT_FOUND"
    message = "해당 옵션(variant)을 찾을 수 없습니다."


class VariantUnavailableError(ConflictError):
    code = "VARIANT_UNAVAILABLE"
    message = "현재 판매하지 않는 옵션입니다."


class InsufficientStockError(ConflictError):
    code = "INSUFFICIENT_STOCK"
    message = "재고가 부족합니다."


class CartItemNotFoundError(NotFoundError):
    code = "NOT_FOUND"
    message = "장바구니 항목을 찾을 수 없습니다."


class CartService:
    def __init__(
        self, cart_repository: CartRepository, product_repository: ProductRepository
    ) -> None:
        self.cart = cart_repository
        self.products = product_repository

    async def _require_variant(self, variant_id: uuid.UUID) -> ProductVariant:
        variant = await self.products.get_variant_by_id(variant_id)
        if variant is None:
            raise VariantNotFoundError()
        if not variant.active:
            raise VariantUnavailableError()
        return variant

    async def add_item(
        self, user_id: uuid.UUID, payload: AddCartItemRequest
    ) -> CartResponse:
        variant = await self._require_variant(payload.variant_id)
        cart = await self.cart.get_or_create_cart(user_id)

        existing = await self.cart.get_item_for_variant(cart.id, variant.id)
        desired_qty = payload.quantity + (existing.quantity if existing else 0)
        if variant.stock < desired_qty:
            raise InsufficientStockError()

        if existing is not None:
            existing.quantity = desired_qty
        else:
            await self.cart.add_item(
                cart_id=cart.id, variant_id=variant.id, quantity=payload.quantity
            )
        return await self._build_cart(cart.id)

    async def get_cart(self, user_id: uuid.UUID) -> CartResponse:
        cart = await self.cart.get_cart_by_user(user_id)
        if cart is None:
            return CartResponse(items=[], totalAmount=0)
        return await self._build_cart(cart.id)

    async def update_item(
        self, user_id: uuid.UUID, cart_item_id: uuid.UUID, payload: UpdateCartItemRequest
    ) -> CartResponse:
        item = await self.cart.get_item_for_user(cart_item_id, user_id)
        if item is None:
            raise CartItemNotFoundError()

        target_variant_id = payload.variant_id or item.variant_id
        variant = await self._require_variant(target_variant_id)
        new_quantity = payload.quantity if payload.quantity is not None else item.quantity

        if payload.variant_id is not None and payload.variant_id != item.variant_id:
            clash = await self.cart.get_item_for_variant(item.cart_id, payload.variant_id)
            if clash is not None:
                raise ConflictError("이미 장바구니에 있는 옵션입니다.")
            item.variant_id = payload.variant_id

        if variant.stock < new_quantity:
            raise InsufficientStockError()
        item.quantity = new_quantity
        return await self._build_cart(item.cart_id)

    async def delete_item(
        self, user_id: uuid.UUID, cart_item_id: uuid.UUID
    ) -> CartResponse:
        item = await self.cart.get_item_for_user(cart_item_id, user_id)
        if item is None:
            raise CartItemNotFoundError()
        cart_id = item.cart_id
        await self.cart.delete_item(item)
        return await self._build_cart(cart_id)

    async def _build_cart(self, cart_id: uuid.UUID) -> CartResponse:
        items = await self.cart.list_items(cart_id)
        variants = await self.products.get_variants_by_ids(
            [i.variant_id for i in items]
        )
        product_ids = [
            v.product_id for v in variants.values()
        ]
        products = await self.products.get_products_by_ids(product_ids)
        thumbs = await self.products.thumbnail_map(product_ids)

        rows: list[CartItemResponse] = []
        total = 0
        currency = "KRW"
        for item in items:
            variant = variants.get(item.variant_id)
            if variant is None:
                continue
            product = products.get(variant.product_id)
            if product is None:
                continue
            line_amount = variant.price * item.quantity
            total += line_amount
            currency = product.currency
            rows.append(
                CartItemResponse(
                    cartItemId=item.id,
                    productId=product.id,
                    productCode=product.product_code,
                    name=product.name,
                    thumbnailFileId=thumbs.get(product.id),
                    variantId=variant.id,
                    sku=variant.sku,
                    color=variant.color,
                    size=variant.size,
                    unitPrice=variant.price,
                    quantity=item.quantity,
                    lineAmount=line_amount,
                    stock=variant.stock,
                )
            )
        return CartResponse(items=rows, totalAmount=total, currency=currency)
