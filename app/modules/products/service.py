"""ProductService — the public contract other domains depend on.

Backend B (OCR, recommendations, cart, orders) calls these methods instead of
touching Product models/repository directly. Returns DTOs, never ORM objects.
"""

import uuid

from app.core.exceptions import NotFoundError
from app.modules.products.models import Product, ProductImage
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import (
    ProductDetail,
    ProductImageInfo,
    ProductSummary,
    ProductTagInfo,
    VariantInfo,
)


class ProductNotFoundError(NotFoundError):
    code = "PRODUCT_NOT_FOUND"
    message = "상품을 찾을 수 없습니다."


def _thumbnail_file_id(images: list[ProductImage]) -> uuid.UUID | None:
    if not images:
        return None
    for image in images:
        if image.type == "thumbnail":
            return image.file_id
    return images[0].file_id  # images are ordered by sortOrder


def _to_variant_info(variant) -> VariantInfo:
    return VariantInfo(
        variantId=variant.id,
        sku=variant.sku,
        color=variant.color,
        size=variant.size,
        price=variant.price,
        stock=variant.stock,
    )


class ProductService:
    def __init__(self, repository: ProductRepository) -> None:
        self.repository = repository

    async def find_by_product_code(self, product_code: str) -> ProductSummary | None:
        product = await self.repository.get_active_by_code(product_code)
        if product is None:
            return None
        images = await self.repository.list_images(product.id)
        return self._to_summary(product, _thumbnail_file_id(images))

    async def get_product(self, product_id: uuid.UUID) -> ProductDetail:
        product = await self.repository.get_active_by_id(product_id)
        if product is None:
            raise ProductNotFoundError()

        images = await self.repository.list_images(product.id)
        tags = await self.repository.list_tags(product.id)
        variants = await self.repository.list_variants(product.id, active_only=True)

        return ProductDetail(
            productId=product.id,
            productCode=product.product_code,
            name=product.name,
            description=product.description,
            category=product.category,
            basePrice=product.base_price,
            currency=product.currency,
            thumbnailFileId=_thumbnail_file_id(images),
            images=[
                ProductImageInfo(fileId=i.file_id, type=i.type, sortOrder=i.sort_order)
                for i in images
            ],
            tags=[ProductTagInfo(tagType=t.tag_type, tagValue=t.tag_value) for t in tags],
            variants=[_to_variant_info(v) for v in variants],
        )

    async def get_available_variants(self, product_id: uuid.UUID) -> list[VariantInfo]:
        product = await self.repository.get_active_by_id(product_id)
        if product is None:
            raise ProductNotFoundError()
        variants = await self.repository.list_variants(product_id, active_only=True)
        return [_to_variant_info(v) for v in variants]

    @staticmethod
    def _to_summary(
        product: Product, thumbnail_file_id: uuid.UUID | None
    ) -> ProductSummary:
        return ProductSummary(
            productId=product.id,
            productCode=product.product_code,
            name=product.name,
            thumbnailFileId=thumbnail_file_id,
            basePrice=product.base_price,
            currency=product.currency,
        )
