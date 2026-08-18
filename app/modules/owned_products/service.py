"""Owned product / after-care business rules (Backend A).

Registers existing products by serial (source=manual) and serves care guides
(per-product, falling back to a category default). Purchased products are
registered automatically by the order flow (source=purchase).
"""

import uuid

from app.api.dependencies.pagination import decode_cursor, encode_cursor, normalize_limit
from app.core.exceptions import ConflictError, NotFoundError
from app.core.responses import PaginationMeta
from app.modules.owned_products.models import RegisteredProduct
from app.modules.owned_products.repository import RegisteredProductRepository
from app.modules.owned_products.schemas import (
    CareGuideResponse,
    RegisteredProductDetail,
    RegisteredProductItem,
    RegisterProductRequest,
)
from app.modules.products.models import Product
from app.modules.products.repository import ProductRepository


class SerialNotFoundError(NotFoundError):
    code = "SERIAL_NOT_FOUND"
    message = "해당 시리얼의 제품을 찾을 수 없습니다."


class AlreadyRegisteredError(ConflictError):
    code = "ALREADY_REGISTERED"
    message = "이미 등록된 시리얼입니다."


# Generic care fallback by product category. Replaced by a per-product
# ProductCareGuide row when one exists.
CATEGORY_CARE_DEFAULTS: dict[str, dict] = {
    "bag": {
        "material": "가죽/패브릭",
        "tips": ["직사광선을 피해 통풍이 잘 되는 곳에 보관", "오염 시 마른 천으로 닦기", "방수 스프레이 주기적 사용"],
    },
    "wallet": {
        "material": "가죽",
        "tips": ["과도한 카드 수납 피하기", "가죽 전용 크림으로 관리", "습기 주의"],
    },
    "apparel": {
        "material": "혼방",
        "tips": ["세탁 라벨 확인 후 세탁", "직사광선 건조 피하기", "다림질은 낮은 온도"],
    },
    "shoes": {
        "material": "가죽/합성",
        "tips": ["착용 후 통풍", "슈트리로 형태 유지", "방수 스프레이 사용"],
    },
}
_DEFAULT_CARE = {
    "material": "제품 소재 확인 필요",
    "tips": ["직사광선/습기를 피해 보관", "부드러운 천으로 관리", "오염은 즉시 제거"],
}


class OwnedProductService:
    def __init__(
        self,
        repository: RegisteredProductRepository,
        product_repository: ProductRepository,
    ) -> None:
        self.repo = repository
        self.products = product_repository

    async def _resolve_serial(self, serial_number: str) -> Product:
        """Placeholder serial resolver.

        No real serial registry exists yet, so a serial is matched against a
        Product.productCode (demo serials == productCode). Replace with a proper
        serial->product mapping once real data is available.
        """
        product = await self.products.get_active_by_code(serial_number)
        if product is None:
            raise SerialNotFoundError()
        return product

    async def register(
        self, user_id: uuid.UUID, payload: RegisterProductRequest
    ) -> RegisteredProductItem:
        product = await self._resolve_serial(payload.serial_number)
        existing = await self.repo.get_by_serial_for_user(payload.serial_number, user_id)
        if existing is not None:
            raise AlreadyRegisteredError()
        row = await self.repo.add_manual(
            user_id=user_id,
            product_id=product.id,
            serial_number=payload.serial_number,
            purchase_date=payload.purchase_date,
            nickname=payload.nickname,
        )
        thumbs = await self.products.thumbnail_map([product.id])
        return self._to_item(row, product, thumbs.get(product.id))

    async def list_products(
        self, user_id: uuid.UUID, *, cursor: str | None = None, limit: int = 20
    ) -> tuple[list[RegisteredProductItem], PaginationMeta]:
        normalized_limit = normalize_limit(limit)
        cursor_created_at, cursor_id = decode_cursor(cursor)
        rows = await self.repo.list_for_user(
            user_id,
            limit=normalized_limit + 1,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        has_next = len(rows) > normalized_limit
        page = rows[:normalized_limit]

        product_ids = [r.product_id for r in page]
        products = await self.products.get_products_by_ids(product_ids)
        thumbs = await self.products.thumbnail_map(product_ids)
        items: list[RegisteredProductItem] = []
        for r in page:
            product = products.get(r.product_id)
            if product is None:
                continue
            items.append(self._to_item(r, product, thumbs.get(product.id)))

        next_cursor = None
        if has_next and page:
            last = page[-1]
            next_cursor = encode_cursor(last.created_at, last.id)
        return items, PaginationMeta(nextCursor=next_cursor, hasNext=has_next, limit=normalized_limit)

    async def get_product(
        self, user_id: uuid.UUID, registration_id: uuid.UUID
    ) -> RegisteredProductDetail:
        row = await self.repo.get_for_user(registration_id, user_id)
        if row is None:
            raise NotFoundError("등록된 제품을 찾을 수 없습니다.")
        products = await self.products.get_products_by_ids([row.product_id])
        product = products.get(row.product_id)
        if product is None:
            raise NotFoundError("상품 정보를 찾을 수 없습니다.")
        thumbs = await self.products.thumbnail_map([product.id])
        return RegisteredProductDetail(
            registrationId=row.id,
            productId=product.id,
            productCode=product.product_code,
            name=product.name,
            thumbnailFileId=thumbs.get(product.id),
            source=row.source,
            serialNumber=row.serial_number,
            nickname=row.nickname,
            purchaseDate=row.purchase_date,
            createdAt=row.created_at,
            category=product.category,
            basePrice=product.base_price,
            currency=product.currency,
        )

    async def get_care_guide(
        self, user_id: uuid.UUID, registration_id: uuid.UUID
    ) -> CareGuideResponse:
        row = await self.repo.get_for_user(registration_id, user_id)
        if row is None:
            raise NotFoundError("등록된 제품을 찾을 수 없습니다.")
        guide = await self.products.get_care_guide(row.product_id)
        if guide is not None:
            return CareGuideResponse(
                productId=row.product_id,
                title=guide.title,
                guide=guide.guide_json,
                asInfo=guide.as_info_json,
                source="product",
            )
        # fallback: category default
        products = await self.products.get_products_by_ids([row.product_id])
        product = products.get(row.product_id)
        category = product.category if product else None
        guide_body = CATEGORY_CARE_DEFAULTS.get(category or "", _DEFAULT_CARE)
        return CareGuideResponse(
            productId=row.product_id,
            title=f"{category or '기본'} 케어 가이드",
            guide=guide_body,
            asInfo=None,
            source="categoryDefault",
        )

    @staticmethod
    def _to_item(
        row: RegisteredProduct, product: Product, thumbnail_file_id: uuid.UUID | None
    ) -> RegisteredProductItem:
        return RegisteredProductItem(
            registrationId=row.id,
            productId=product.id,
            productCode=product.product_code,
            name=product.name,
            thumbnailFileId=thumbnail_file_id,
            source=row.source,
            serialNumber=row.serial_number,
            nickname=row.nickname,
            purchaseDate=row.purchase_date,
            createdAt=row.created_at,
        )
