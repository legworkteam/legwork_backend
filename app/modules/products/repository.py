"""Persistence for the product catalog (Backend A)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.products.models import (
    Product,
    ProductCareGuide,
    ProductImage,
    ProductTag,
    ProductVariant,
    RecentProduct,
)
from app.utils.datetime import now_kst


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

    async def get_variant_by_id(self, variant_id: uuid.UUID) -> ProductVariant | None:
        return await self.session.get(ProductVariant, variant_id)

    async def get_care_guide(self, product_id: uuid.UUID) -> ProductCareGuide | None:
        return await self.session.scalar(
            select(ProductCareGuide).where(ProductCareGuide.product_id == product_id)
        )

    async def get_products_by_ids(
        self, product_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, Product]:
        if not product_ids:
            return {}
        rows = await self.session.scalars(
            select(Product).where(Product.id.in_(product_ids))
        )
        return {p.id: p for p in rows}

    async def get_variants_by_ids(
        self, variant_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, ProductVariant]:
        if not variant_ids:
            return {}
        rows = await self.session.scalars(
            select(ProductVariant).where(ProductVariant.id.in_(variant_ids))
        )
        return {v.id: v for v in rows}

    async def list_variants(
        self, product_id: uuid.UUID, *, active_only: bool = True
    ) -> list[ProductVariant]:
        stmt = select(ProductVariant).where(ProductVariant.product_id == product_id)
        if active_only:
            stmt = stmt.where(ProductVariant.active.is_(True))
        stmt = stmt.order_by(ProductVariant.color, ProductVariant.size)
        result = await self.session.scalars(stmt)
        return list(result)

    async def thumbnail_map(
        self, product_ids: list[uuid.UUID]
    ) -> dict[uuid.UUID, uuid.UUID]:
        """productId -> thumbnail fileId (type='thumbnail' first, else lowest sortOrder)."""
        if not product_ids:
            return {}
        images = await self.session.scalars(
            select(ProductImage)
            .where(ProductImage.product_id.in_(product_ids))
            .order_by(ProductImage.sort_order)
        )
        result: dict[uuid.UUID, uuid.UUID] = {}
        for image in images:
            current = result.get(image.product_id)
            if current is None:
                result[image.product_id] = image.file_id
            if image.type == "thumbnail":
                result[image.product_id] = image.file_id
        return result


class RecentProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_for_owner(
        self,
        *,
        product_id: uuid.UUID,
        user_id: uuid.UUID | None,
        guest_session_id: uuid.UUID | None,
    ) -> RecentProduct | None:
        stmt = select(RecentProduct).where(RecentProduct.product_id == product_id)
        if user_id is not None:
            stmt = stmt.where(RecentProduct.user_id == user_id)
        else:
            stmt = stmt.where(RecentProduct.guest_session_id == guest_session_id)
        return await self.session.scalar(stmt)

    async def upsert(
        self,
        *,
        product_id: uuid.UUID,
        user_id: uuid.UUID | None,
        guest_session_id: uuid.UUID | None,
    ) -> None:
        existing = await self.get_for_owner(
            product_id=product_id, user_id=user_id, guest_session_id=guest_session_id
        )
        if existing is not None:
            existing.viewed_at = now_kst()
            return
        self.session.add(
            RecentProduct(
                product_id=product_id,
                user_id=user_id,
                guest_session_id=guest_session_id,
                viewed_at=now_kst(),
            )
        )
        await self.session.flush()

    async def list_for_guest(
        self, guest_session_id: uuid.UUID
    ) -> list[RecentProduct]:
        result = await self.session.scalars(
            select(RecentProduct).where(
                RecentProduct.guest_session_id == guest_session_id
            )
        )
        return list(result)

    async def delete(self, row: RecentProduct) -> None:
        await self.session.delete(row)

    async def list_recent(
        self,
        *,
        user_id: uuid.UUID | None,
        guest_session_id: uuid.UUID | None,
        limit: int,
    ) -> list[tuple[Product, object]]:
        """Return (Product, viewedAt) rows, most-recent first, active products only."""
        stmt = (
            select(Product, RecentProduct.viewed_at)
            .join(RecentProduct, RecentProduct.product_id == Product.id)
            .where(Product.active.is_(True))
        )
        if user_id is not None:
            stmt = stmt.where(RecentProduct.user_id == user_id)
        else:
            stmt = stmt.where(RecentProduct.guest_session_id == guest_session_id)
        stmt = stmt.order_by(RecentProduct.viewed_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
