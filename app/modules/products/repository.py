"""Persistence for the product catalog (Backend A)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.products.models import (
    Product,
    ProductImage,
    ProductTag,
    ProductVariant,
)


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_by_code(self, product_code: str) -> Product | None:
        return await self.session.scalar(
            select(Product).where(
                Product.product_code == product_code, Product.active.is_(True)
            )
        )

    async def get_active_by_id(self, product_id: uuid.UUID) -> Product | None:
        return await self.session.scalar(
            select(Product).where(Product.id == product_id, Product.active.is_(True))
        )

    async def list_images(self, product_id: uuid.UUID) -> list[ProductImage]:
        result = await self.session.scalars(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order)
        )
        return list(result)

    async def list_tags(self, product_id: uuid.UUID) -> list[ProductTag]:
        result = await self.session.scalars(
            select(ProductTag).where(ProductTag.product_id == product_id)
        )
        return list(result)

    async def list_variants(
        self, product_id: uuid.UUID, *, active_only: bool = True
    ) -> list[ProductVariant]:
        stmt = select(ProductVariant).where(ProductVariant.product_id == product_id)
        if active_only:
            stmt = stmt.where(ProductVariant.active.is_(True))
        stmt = stmt.order_by(ProductVariant.color, ProductVariant.size)
        result = await self.session.scalars(stmt)
        return list(result)
