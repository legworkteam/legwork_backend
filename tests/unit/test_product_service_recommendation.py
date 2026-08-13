from uuid import uuid4

import pytest

from app.modules.products.models import Product, ProductImage, ProductTag, ProductVariant
from app.modules.products.repository import ProductRepository
from app.modules.products.service import ProductService


async def _create_product(
    db_session,
    *,
    name: str,
    code: str,
    active: bool = True,
) -> Product:
    product = Product(
        product_code=code,
        name=name,
        description=f"{name} description",
        category="bag",
        base_price=1000,
        currency="KRW",
        active=active,
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest.mark.asyncio
async def test_list_recommendation_candidates_returns_active_products_only_and_excludes_base(db_session) -> None:
    base = await _create_product(db_session, name="Base", code="BASE-001")
    active = await _create_product(db_session, name="Alpha", code="ALPHA-001")
    inactive = await _create_product(db_session, name="Inactive", code="INACTIVE-001", active=False)
    db_session.add_all(
        [
            ProductTag(product_id=active.id, tag_type="style", tag_value="casual"),
            ProductVariant(product_id=active.id, sku="SKU-ACTIVE", color="black", size="M", price=1000, stock=5, active=True),
            ProductVariant(product_id=active.id, sku="SKU-INACTIVE", color="black", size="L", price=1000, stock=5, active=False),
            ProductImage(product_id=active.id, file_id=uuid4(), type="thumbnail", sort_order=0),
            ProductTag(product_id=inactive.id, tag_type="style", tag_value="casual"),
            ProductVariant(product_id=inactive.id, sku="SKU-OFF", color="black", size="M", price=1000, stock=5, active=True),
        ]
    )
    await db_session.commit()

    service = ProductService(ProductRepository(db_session))
    candidates = await service.list_recommendation_candidates(
        exclude_product_id=base.id,
        limit=10,
    )

    assert [item.product_code for item in candidates] == ["ALPHA-001"]
    assert candidates[0].tags[0].tag_type == "style"
    assert len(candidates[0].variants) == 1
    assert candidates[0].variants[0].sku == "SKU-ACTIVE"


@pytest.mark.asyncio
async def test_list_recommendation_candidates_applies_limit_and_deterministic_order(db_session) -> None:
    base = await _create_product(db_session, name="Base", code="BASE-001")
    for name, code in [("Charlie", "C-001"), ("Alpha", "A-001"), ("Bravo", "B-001")]:
        product = await _create_product(db_session, name=name, code=code)
        db_session.add(ProductVariant(product_id=product.id, sku=f"SKU-{code}", color="black", size="M", price=1000, stock=5, active=True))
    await db_session.commit()

    service = ProductService(ProductRepository(db_session))
    candidates = await service.list_recommendation_candidates(
        exclude_product_id=base.id,
        limit=2,
    )

    assert [item.product_code for item in candidates] == ["A-001", "B-001"]
