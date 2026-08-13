"""Persistence for registered (owned) products (Backend A)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import RegisteredProductSource
from app.modules.owned_products.models import RegisteredProduct


class RegisteredProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_user(self, user_id: uuid.UUID) -> list[RegisteredProduct]:
        result = await self.session.scalars(
            select(RegisteredProduct)
            .where(RegisteredProduct.user_id == user_id)
            .order_by(RegisteredProduct.created_at.desc())
        )
        return list(result)

    async def get_for_user(
        self, registration_id: uuid.UUID, user_id: uuid.UUID
    ) -> RegisteredProduct | None:
        return await self.session.scalar(
            select(RegisteredProduct).where(
                RegisteredProduct.id == registration_id,
                RegisteredProduct.user_id == user_id,
            )
        )

    async def get_by_serial_for_user(
        self, serial_number: str, user_id: uuid.UUID
    ) -> RegisteredProduct | None:
        return await self.session.scalar(
            select(RegisteredProduct).where(
                RegisteredProduct.user_id == user_id,
                RegisteredProduct.serial_number == serial_number,
            )
        )

    async def add_manual(
        self,
        *,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        serial_number: str,
        purchase_date=None,
        nickname: str | None = None,
    ) -> RegisteredProduct:
        row = RegisteredProduct(
            user_id=user_id,
            product_id=product_id,
            source=RegisteredProductSource.MANUAL,
            serial_number=serial_number,
            purchase_date=purchase_date,
            nickname=nickname,
        )
        self.session.add(row)
        await self.session.flush()
        return row
