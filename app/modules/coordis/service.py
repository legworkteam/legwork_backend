from __future__ import annotations

import base64
import uuid
from datetime import datetime

from app.core.responses import PaginationMeta
from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.modules.coordis.models import SavedCoordi, SavedCoordiItem
from app.modules.coordis.repository import SavedCoordiRepository
from app.modules.coordis.schemas import (
    SavedCoordiCreateRequest,
    SavedCoordiDetail,
    SavedCoordiItemDetail,
    SavedCoordiItemPayload,
    SavedCoordiSummary,
    SavedCoordiUpdateRequest,
)
from app.modules.products.schemas import ProductSummary, VariantInfo
from app.modules.products.service import ProductService
from app.utils.datetime import now_kst


DEFAULT_COORDI_LIMIT = 20
MAX_COORDI_LIMIT = 50


class SavedCoordiNotFoundError(NotFoundError):
    code = "SAVED_COORDI_NOT_FOUND"
    message = "Saved coordi not found."


class SavedCoordiService:
    def __init__(
        self,
        repository: SavedCoordiRepository,
        *,
        product_service: ProductService,
    ) -> None:
        self.repository = repository
        self.session = repository.session
        self.product_service = product_service

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        payload: SavedCoordiCreateRequest,
    ) -> SavedCoordiDetail:
        _, thumbnail_file_id = await self._validate_items(payload.items)
        row = SavedCoordi(
            user_id=user_id,
            name=payload.name,
            thumbnail_file_id=thumbnail_file_id,
        )
        await self.repository.add(row)
        await self.repository.add_items(
            [
                SavedCoordiItem(
                    saved_coordi_id=row.id,
                    product_id=item.product_id,
                    variant_id=item.variant_id,
                    sort_order=index,
                )
                for index, item in enumerate(payload.items)
            ]
        )
        await self.session.commit()
        item_rows = await self.repository.list_items(row.id)
        return SavedCoordiDetail(
            savedCoordiId=row.id,
            name=row.name,
            thumbnailFileId=row.thumbnail_file_id,
            createdAt=row.created_at,
            updatedAt=row.updated_at,
            items=await self._build_item_details(item_rows),
        )

    async def list_owned(
        self,
        *,
        user_id: uuid.UUID,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[SavedCoordiSummary], PaginationMeta]:
        normalized_limit = max(1, min(limit, MAX_COORDI_LIMIT))
        cursor_created_at, cursor_id = self._decode_cursor(cursor)
        rows = await self.repository.list_page(
            user_id=user_id,
            limit=normalized_limit + 1,
            cursor_created_at=cursor_created_at,
            cursor_id=cursor_id,
        )
        has_next = len(rows) > normalized_limit
        page = rows[:normalized_limit]
        next_cursor = None
        if has_next and page:
            last = page[-1]
            next_cursor = self._encode_cursor(last.created_at, last.id)
        return (
            [SavedCoordiSummary.model_validate(row) for row in page],
            PaginationMeta(nextCursor=next_cursor, hasNext=has_next, limit=normalized_limit),
        )

    async def get_owned(self, *, saved_coordi_id: uuid.UUID, user_id: uuid.UUID) -> SavedCoordiDetail:
        row = await self.repository.get_owned(saved_coordi_id=saved_coordi_id, user_id=user_id)
        if row is None:
            raise SavedCoordiNotFoundError()
        item_rows = await self.repository.list_items(row.id)
        items = await self._build_item_details(item_rows)
        return SavedCoordiDetail(
            savedCoordiId=row.id,
            name=row.name,
            thumbnailFileId=row.thumbnail_file_id,
            createdAt=row.created_at,
            updatedAt=row.updated_at,
            items=items,
        )

    async def update(
        self,
        *,
        saved_coordi_id: uuid.UUID,
        user_id: uuid.UUID,
        payload: SavedCoordiUpdateRequest,
    ) -> SavedCoordiDetail:
        row = await self.repository.get_owned(saved_coordi_id=saved_coordi_id, user_id=user_id)
        if row is None:
            raise SavedCoordiNotFoundError()

        item_details: list[SavedCoordiItemDetail] | None = None
        thumbnail_file_id = row.thumbnail_file_id
        if payload.items is not None:
            _, thumbnail_file_id = await self._validate_items(payload.items)

        if payload.name is not None:
            row.name = payload.name
        if payload.items is not None:
            row.thumbnail_file_id = thumbnail_file_id
            await self.repository.replace_items(
                saved_coordi_id=row.id,
                rows=[
                    SavedCoordiItem(
                        saved_coordi_id=row.id,
                        product_id=item.product_id,
                        variant_id=item.variant_id,
                        sort_order=index,
                    )
                    for index, item in enumerate(payload.items)
                ],
            )
        row.updated_at = now_kst()
        await self.session.commit()
        await self.session.refresh(row)

        item_details = await self._build_item_details(await self.repository.list_items(row.id))
        return SavedCoordiDetail(
            savedCoordiId=row.id,
            name=row.name,
            thumbnailFileId=row.thumbnail_file_id,
            createdAt=row.created_at,
            updatedAt=row.updated_at,
            items=item_details,
        )

    async def delete(self, *, saved_coordi_id: uuid.UUID, user_id: uuid.UUID) -> None:
        row = await self.repository.get_owned(saved_coordi_id=saved_coordi_id, user_id=user_id)
        if row is None:
            raise SavedCoordiNotFoundError()
        row.deleted_at = now_kst()
        row.updated_at = row.deleted_at
        await self.session.commit()

    async def get_owned_items_for_try_on(
        self,
        *,
        saved_coordi_id: uuid.UUID,
        user_id: uuid.UUID | None,
    ) -> list[SavedCoordiItemDetail]:
        if user_id is None:
            raise ForbiddenError("Only members can use saved coordi try-on.")
        row = await self.repository.get_owned(saved_coordi_id=saved_coordi_id, user_id=user_id)
        if row is None:
            raise SavedCoordiNotFoundError()
        return await self._build_item_details(await self.repository.list_items(row.id))

    async def _validate_items(
        self,
        items: list[SavedCoordiItemPayload],
    ) -> tuple[list[SavedCoordiItemDetail], uuid.UUID | None]:
        if not items:
            raise ValidationError("items must not be empty.")

        seen: set[tuple[uuid.UUID, uuid.UUID | None]] = set()
        item_details: list[SavedCoordiItemDetail] = []
        thumbnail_file_id: uuid.UUID | None = None

        for index, item in enumerate(items):
            key = (item.product_id, item.variant_id)
            if key in seen:
                raise ValidationError(
                    "Duplicate coordi item is not allowed.",
                    details={"field": "items", "productId": str(item.product_id), "variantId": str(item.variant_id) if item.variant_id else None},
                )
            seen.add(key)

            product = await self.product_service.get_product(item.product_id)
            product_summary = ProductSummary(
                productId=product.product_id,
                productCode=product.product_code,
                name=product.name,
                thumbnailFileId=product.thumbnail_file_id,
                basePrice=product.base_price,
                currency=product.currency,
            )
            if thumbnail_file_id is None:
                thumbnail_file_id = product.thumbnail_file_id

            variant_info: VariantInfo | None = None
            if item.variant_id is not None:
                variants = await self.product_service.get_available_variants(item.product_id)
                variant_info = next((variant for variant in variants if variant.variant_id == item.variant_id), None)
                if variant_info is None:
                    raise ValidationError(
                        "variantId must belong to the product and be active.",
                        details={"field": "variantId", "productId": str(item.product_id), "variantId": str(item.variant_id)},
                    )

            item_details.append(
                SavedCoordiItemDetail(
                    savedCoordiItemId=uuid.uuid4(),
                    productId=item.product_id,
                    variantId=item.variant_id,
                    sortOrder=index,
                    product=product_summary,
                    variant=variant_info,
                )
            )

        return item_details, thumbnail_file_id

    async def _build_item_details(self, item_rows: list[SavedCoordiItem]) -> list[SavedCoordiItemDetail]:
        details: list[SavedCoordiItemDetail] = []
        for row in item_rows:
            product = await self.product_service.get_product(row.product_id)
            variants = await self.product_service.get_available_variants(row.product_id)
            variant_info = next((variant for variant in variants if variant.variant_id == row.variant_id), None)
            details.append(
                SavedCoordiItemDetail(
                    savedCoordiItemId=row.id,
                    productId=row.product_id,
                    variantId=row.variant_id,
                    sortOrder=row.sort_order,
                    product=ProductSummary(
                        productId=product.product_id,
                        productCode=product.product_code,
                        name=product.name,
                        thumbnailFileId=product.thumbnail_file_id,
                        basePrice=product.base_price,
                        currency=product.currency,
                    ),
                    variant=variant_info,
                )
            )
        return details

    @staticmethod
    def _encode_cursor(created_at: datetime, row_id: uuid.UUID) -> str:
        raw = f"{created_at.isoformat()}|{row_id}"
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")

    @staticmethod
    def _decode_cursor(cursor: str | None) -> tuple[datetime | None, uuid.UUID | None]:
        if cursor is None:
            return None, None
        try:
            raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
            created_at_raw, row_id_raw = raw.split("|", 1)
            return datetime.fromisoformat(created_at_raw), uuid.UUID(row_id_raw)
        except Exception as exc:
            raise ValidationError("Invalid cursor.") from exc
