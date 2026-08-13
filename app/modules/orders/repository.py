"""Persistence for orders, order items, and payments (Backend A)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import OrderStatus
from app.modules.orders.models import Order, OrderItem, Payment


class OrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_order(
        self, *, user_id: uuid.UUID, total_amount: int, currency: str
    ) -> Order:
        order = Order(
            user_id=user_id,
            status=OrderStatus.PENDING,
            total_amount=total_amount,
            currency=currency,
        )
        self.session.add(order)
        await self.session.flush()
        return order

    async def add_item(self, item: OrderItem) -> OrderItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def add_payment(self, payment: Payment) -> Payment:
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def list_orders_for_user(self, user_id: uuid.UUID) -> list[Order]:
        result = await self.session.scalars(
            select(Order)
            .where(Order.user_id == user_id, Order.deleted_at.is_(None))
            .order_by(Order.created_at.desc())
        )
        return list(result)

    async def get_order_for_user(
        self, order_id: uuid.UUID, user_id: uuid.UUID
    ) -> Order | None:
        return await self.session.scalar(
            select(Order).where(
                Order.id == order_id,
                Order.user_id == user_id,
                Order.deleted_at.is_(None),
            )
        )

    async def list_items(self, order_id: uuid.UUID) -> list[OrderItem]:
        result = await self.session.scalars(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        return list(result)

    async def latest_payment(self, order_id: uuid.UUID) -> Payment | None:
        return await self.session.scalar(
            select(Payment)
            .where(Payment.order_id == order_id)
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
