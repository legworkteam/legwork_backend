"""Demo seed data for Atelier Lens (Backend A domains).

Idempotent: safe to run multiple times — existing rows (by unique key) are
reused, not duplicated. Also self-healing: if a product's ProductImage points
to a fileId with no matching FileMetadata (e.g. from an older seed run before
public product images existed), it backfills a real file. Run with:

    .venv/Scripts/python.exe -m scripts.seed

Creates stores, a campaign + QR opaque code, and a demo product catalog
(products / variants / tags / images / care guides). Product codes use a
DEMO- prefix until real MCM 품번 data is available. Product thumbnails are
real generated placeholder PNGs stored as public FileMetadata (fetchable via
GET /files/{fileId} without auth-owner checks).
"""

import asyncio
import uuid

import cv2
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.enums import FileOwnerType, FileVisibility, RegisteredProductSource  # noqa: F401
from app.modules.files.models import FileMetadata
from app.modules.products.models import (
    Product,
    ProductCareGuide,
    ProductImage,
    ProductTag,
    ProductVariant,
)
from app.modules.stores.models import Campaign, QrCodeMapping, Store
from app.storage.local import LocalStorageService
from app.storage.paths import build_private_upload_path

# --- catalog definition ------------------------------------------------------
# Each product: code, name, category, basePrice, tags {style,color,season},
# variants [(color, size, price, stock)], and an optional care guide.
CATALOG: list[dict] = [
    {
        "code": "DEMO-BAG-001", "name": "Aren Backpack", "category": "bag",
        "price": 890000,
        "tags": {"style": "casual", "color": "black", "season": "all"},
        "variants": [("black", "M", 890000, 6), ("brown", "M", 910000, 4)],
        "care": {"title": "Aren Backpack 케어", "guide": {"material": "코팅 캔버스", "tips": ["마른 천으로 오염 제거", "직사광선 피하기"]}, "asInfo": {"warranty": "1년"}},
    },
    {
        "code": "DEMO-BAG-002", "name": "Luna Tote", "category": "bag",
        "price": 1250000,
        "tags": {"style": "formal", "color": "beige", "season": "spring"},
        "variants": [("beige", "L", 1250000, 3), ("black", "L", 1250000, 5)],
    },
    {
        "code": "DEMO-BAG-003", "name": "Mini Crossbody", "category": "bag",
        "price": 690000,
        "tags": {"style": "casual", "color": "red", "season": "summer"},
        "variants": [("red", "S", 690000, 8), ("white", "S", 690000, 2)],
    },
    {
        "code": "DEMO-WAL-001", "name": "Fold Wallet", "category": "wallet",
        "price": 320000,
        "tags": {"style": "classic", "color": "brown", "season": "all"},
        "variants": [("brown", "F", 320000, 10), ("black", "F", 320000, 10)],
        "care": {"title": "Fold Wallet 케어", "guide": {"material": "천연 가죽", "tips": ["가죽 크림 사용", "습기 주의"]}, "asInfo": None},
    },
    {
        "code": "DEMO-WAL-002", "name": "Zip Card Holder", "category": "wallet",
        "price": 180000,
        "tags": {"style": "minimal", "color": "navy", "season": "all"},
        "variants": [("navy", "F", 180000, 12)],
    },
    {
        "code": "DEMO-APP-001", "name": "Wool Coat", "category": "apparel",
        "price": 1490000,
        "tags": {"style": "formal", "color": "camel", "season": "winter"},
        "variants": [("camel", "M", 1490000, 4), ("camel", "L", 1490000, 3), ("gray", "M", 1490000, 2)],
    },
    {
        "code": "DEMO-APP-002", "name": "Knit Sweater", "category": "apparel",
        "price": 420000,
        "tags": {"style": "casual", "color": "ivory", "season": "winter"},
        "variants": [("ivory", "S", 420000, 7), ("ivory", "M", 420000, 6), ("green", "M", 420000, 5)],
    },
    {
        "code": "DEMO-APP-003", "name": "Silk Blouse", "category": "apparel",
        "price": 380000,
        "tags": {"style": "formal", "color": "white", "season": "spring"},
        "variants": [("white", "S", 380000, 5), ("blue", "M", 380000, 4)],
    },
    {
        "code": "DEMO-SHO-001", "name": "Leather Loafer", "category": "shoes",
        "price": 560000,
        "tags": {"style": "classic", "color": "black", "season": "all"},
        "variants": [("black", "260", 560000, 5), ("black", "270", 560000, 4), ("brown", "270", 560000, 3)],
        "care": {"title": "Leather Loafer 케어", "guide": {"material": "소가죽", "tips": ["슈트리로 형태 유지", "방수 스프레이"]}, "asInfo": {"repair": "밑창 교체 가능"}},
    },
    {
        "code": "DEMO-SHO-002", "name": "Suede Sneaker", "category": "shoes",
        "price": 490000,
        "tags": {"style": "casual", "color": "gray", "season": "spring"},
        "variants": [("gray", "260", 490000, 6), ("white", "270", 490000, 4)],
    },
    {
        "code": "DEMO-ACC-001", "name": "Silk Scarf", "category": "accessory",
        "price": 250000,
        "tags": {"style": "formal", "color": "multi", "season": "all"},
        "variants": [("multi", "F", 250000, 9)],
    },
    {
        "code": "DEMO-ACC-002", "name": "Leather Belt", "category": "accessory",
        "price": 210000,
        "tags": {"style": "classic", "color": "black", "season": "all"},
        "variants": [("black", "90", 210000, 8), ("brown", "95", 210000, 6)],
    },
]


def _placeholder_png(*, code: str, name: str, category: str) -> bytes:
    """Small generated placeholder product image (demo-only, real photos come later)."""
    canvas = np.full((480, 480, 3), 238, dtype=np.uint8)
    cv2.rectangle(canvas, (16, 16), (464, 464), (200, 190, 175), 3)
    cv2.putText(canvas, "ATELIER LENS", (36, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (90, 80, 70), 2, cv2.LINE_AA)
    cv2.putText(canvas, category.upper(), (36, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (60, 60, 60), 2, cv2.LINE_AA)
    cv2.putText(canvas, name, (36, 270), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 1, cv2.LINE_AA)
    cv2.putText(canvas, code, (36, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 110, 100), 1, cv2.LINE_AA)
    ok, encoded = cv2.imencode(".png", canvas)
    if not ok:
        raise RuntimeError("Failed to encode placeholder product image.")
    return encoded.tobytes()


async def _ensure_product_thumbnail(
    session: AsyncSession, storage: LocalStorageService, product: Product
) -> None:
    """Create (or backfill) a real public FileMetadata-backed thumbnail."""
    image = await session.scalar(
        select(ProductImage)
        .where(ProductImage.product_id == product.id)
        .order_by(ProductImage.sort_order.asc(), ProductImage.id.asc())
    )
    if image is not None:
        backing = await session.scalar(
            select(FileMetadata).where(FileMetadata.id == image.file_id)
        )
        if backing is not None:
            return  # already has a real file behind it

    file_id = uuid.uuid4()
    filename = f"{product.product_code}.png"
    relative_path = build_private_upload_path(
        owner_type=FileOwnerType.PRODUCT, owner_id=product.id, file_id=file_id, filename=filename
    )
    content = _placeholder_png(code=product.product_code, name=product.name, category=product.category or "")
    write_result = await storage.save(relative_path=relative_path, content=content)
    session.add(
        FileMetadata(
            id=file_id,
            owner_type=FileOwnerType.PRODUCT,
            owner_id=product.id,
            path=write_result.relative_path,
            original_name=filename,
            content_type="image/png",
            size=write_result.size,
            visibility=FileVisibility.PUBLIC,
        )
    )
    if image is None:
        session.add(ProductImage(product_id=product.id, file_id=file_id, type="thumbnail", sort_order=0))
    else:
        image.file_id = file_id


async def _get_or_create_store(session: AsyncSession, name: str, address: str) -> Store:
    store = await session.scalar(select(Store).where(Store.name == name))
    if store is None:
        store = Store(name=name, address=address, active=True)
        session.add(store)
        await session.flush()
    return store


async def _get_or_create_campaign(session: AsyncSession, name: str) -> Campaign:
    campaign = await session.scalar(select(Campaign).where(Campaign.name == name))
    if campaign is None:
        campaign = Campaign(name=name, active=True)
        session.add(campaign)
        await session.flush()
    return campaign


async def _get_or_create_qr(
    session: AsyncSession, code: str, store: Store, campaign: Campaign
) -> QrCodeMapping:
    qr = await session.scalar(select(QrCodeMapping).where(QrCodeMapping.code == code))
    if qr is None:
        qr = QrCodeMapping(
            code=code, store_id=store.id, campaign_id=campaign.id, active=True
        )
        session.add(qr)
        await session.flush()
    return qr


async def _seed_product(session: AsyncSession, storage: LocalStorageService, spec: dict) -> bool:
    """Upsert a product with variants/tags/image/care-guide. Returns True if new."""
    product = await session.scalar(
        select(Product).where(Product.product_code == spec["code"])
    )
    created = False
    if product is None:
        product = Product(
            product_code=spec["code"],
            name=spec["name"],
            category=spec["category"],
            base_price=spec["price"],
            currency="KRW",
            active=True,
        )
        session.add(product)
        await session.flush()
        created = True
    else:
        product.name = spec["name"]
        product.category = spec["category"]
        product.base_price = spec["price"]
        product.currency = "KRW"
        product.active = True

    existing_variants = {
        variant.sku: variant
        for variant in (
            await session.scalars(
                select(ProductVariant).where(ProductVariant.product_id == product.id)
            )
        )
    }
    for i, (color, size, price, stock) in enumerate(spec["variants"]):
        sku = f"{spec['code']}-{color[:3].upper()}-{size}-{i}"
        variant = existing_variants.get(sku)
        if variant is None:
            variant = ProductVariant(
                product_id=product.id,
                sku=sku,
                color=color,
                size=size,
                price=price,
                stock=stock,
                active=True,
            )
            session.add(variant)
        else:
            variant.color = color
            variant.size = size
            variant.price = price
            variant.stock = stock
            variant.active = True

    existing_tags = {
        (tag.tag_type, tag.tag_value)
        for tag in (
            await session.scalars(
                select(ProductTag).where(ProductTag.product_id == product.id)
            )
        )
    }
    for tag_type, tag_value in spec["tags"].items():
        if (tag_type, tag_value) not in existing_tags:
            session.add(
                ProductTag(product_id=product.id, tag_type=tag_type, tag_value=tag_value)
            )

    await _ensure_product_thumbnail(session, storage, product)

    care = spec.get("care")
    if care:
        existing_care = await session.scalar(
            select(ProductCareGuide).where(ProductCareGuide.product_id == product.id)
        )
        if existing_care is None:
            session.add(
                ProductCareGuide(
                    product_id=product.id,
                    title=care["title"],
                    guide_json=care["guide"],
                    as_info_json=care.get("asInfo"),
                )
            )
        else:
            existing_care.title = care["title"]
            existing_care.guide_json = care["guide"]
            existing_care.as_info_json = care.get("asInfo")
    return created


async def seed() -> None:
    storage = LocalStorageService()
    async with AsyncSessionLocal() as session:
        flagship = await _get_or_create_store(session, "MCM 플래그십", "서울시 강남구")
        popup = await _get_or_create_store(session, "Atelier Lens 팝업", "서울시 성수동")
        campaign = await _get_or_create_campaign(session, "Atelier Lens Demo")
        await _get_or_create_qr(session, "a7B9x2", flagship, campaign)
        await _get_or_create_qr(session, "demo01", popup, campaign)

        created = 0
        for spec in CATALOG:
            if await _seed_product(session, storage, spec):
                created += 1

        await session.commit()

    print(
        f"Seed complete: stores(2), campaign(1), qr(2), products +{created}/{len(CATALOG)}"
    )


if __name__ == "__main__":
    asyncio.run(seed())
