"""Persistence for cart and cart items (Backend A)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cart.models import Cart, CartItem


class CartRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_cart_by_user(self, user_id: uuid.UUID) -> Cart | None:
        return await self.session.scalar(select(Cart).where(Cart.user_id == user_id))

    async def create_cart(self, user_id: uuid.UUID) -> Cart:
        cart = Cart(user_id=user_id)
        self.session.add(cart)
        await self.session.flush()
        return cart

    async def get_or_create_cart(self, user_id: uuid.UUID) -> Cart:
        cart = await self.get_cart_by_user(user_id)
        if cart is None:
            cart = await self.create_cart(user_id)
        return cart

    async def list_items(self, cart_id: uuid.UUID) -> list[CartItem]:
        result = await self.session.scalars(
            select(CartItem)
            .where(CartItem.cart_id == cart_id)
            .order_by(CartItem.created_at)
        )
        return list(result)

    async def get_item_for_variant(
        self, cart_id: uuid.UUID, variant_id: uuid.UUID
    ) -> CartItem | None:
        return await self.session.scalar(
            select(CartItem).where(
                CartItem.cart_id == cart_id, CartItem.variant_id == variant_id
            )
        )

    async def get_item_for_user(
        self, cart_item_id: uuid.UUID, user_id: uuid.UUID
    ) -> CartItem | None:
        return await self.session.scalar(
            select(CartItem)
            .join(Cart, Cart.id == CartItem.cart_id)
            .where(CartItem.id == cart_item_id, Cart.user_id == user_id)
        )

    async def get_items_for_user(
        self, cart_item_ids: list[uuid.UUID], user_id: uuid.UUID
    ) -> list[CartItem]:
        if not cart_item_ids:
            return []
        result = await self.session.scalars(
            select(CartItem)
            .join(Cart, Cart.id == CartItem.cart_id)
            .where(CartItem.id.in_(cart_item_ids), Cart.user_id == user_id)
        )
        return list(result)

    async def add_item(
        self, *, cart_id: uuid.UUID, variant_id: uuid.UUID, quantity: int
    ) -> CartItem:
        item = CartItem(cart_id=cart_id, variant_id=variant_id, quantity=quantity)
        self.session.add(item)
        await self.session.flush()
        return item

    async def delete_item(self, item: CartItem) -> None:
        await self.session.delete(item)
