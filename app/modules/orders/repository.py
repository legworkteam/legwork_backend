"""Persistence for orders, order items, and payments (Backend A)."""

import uuid
from datetime import datetime

from sqlalchemy import and_, or_, select
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

    async def list_orders_for_user(
        self,
        user_id: uuid.UUID,
        *,
        limit: int,
        cursor_created_at: datetime | None = None,
        cursor_id: uuid.UUID | None = None,
    ) -> list[Order]:
        stmt = select(Order).where(Order.user_id == user_id, Order.deleted_at.is_(None))
        if cursor_created_at is not None and cursor_id is not None:
            stmt = stmt.where(
                or_(
                    Order.created_at < cursor_created_at,
                    and_(Order.created_at == cursor_created_at, Order.id < cursor_id),
                )
            )
        stmt = stmt.order_by(Order.created_at.desc(), Order.id.desc()).limit(limit)
        result = await self.session.scalars(stmt)
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
