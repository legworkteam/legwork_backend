from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.enums import AuthProvider
from app.core.security import create_access_token
from app.modules.products.models import Product, ProductTag, ProductVariant
from app.modules.users.models import User


async def _create_user(db_session, name: str = "ProdMember") -> User:
    user = User(
        name=name,
        email=f"{name.lower()}-{uuid4().hex}@example.com",
        auth_provider=AuthProvider.LOCAL,
        provider_user_id=None,
        password_hash="hash",
        phone=None,
        login_fail_count=0,
        locked_until=None,
        deleted_at=None,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


async def _create_product(db_session, *, code: str | None = None) -> Product:
    product = Product(
        product_code=code or f"PROD-{uuid4().hex[:8]}",
        name="Test Bag",
        category="bag",
        base_price=500000,
        currency="KRW",
        active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    db_session.add_all(
        [
            ProductVariant(
                product_id=product.id, sku=f"{product.product_code}-BLK",
                color="black", size="M", price=500000, stock=3, active=True,
            ),
            ProductVariant(
                product_id=product.id, sku=f"{product.product_code}-OFF",
                color="red", size="S", price=1, stock=9, active=False,
            ),
            ProductTag(product_id=product.id, tag_type="style", tag_value="casual"),
        ]
    )
    await db_session.commit()
    return product


@pytest.mark.asyncio
async def test_get_product_detail_returns_active_variants_and_tags(
    db_session, client: TestClient
) -> None:
    user = await _create_user(db_session)
    product = await _create_product(db_session)
    token = create_access_token(str(user.id))

    response = client.get(
        f"/api/v1/products/{product.id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Test Bag"
    assert len(data["variants"]) == 1  # inactive variant excluded
    assert data["variants"][0]["color"] == "black"
    assert data["tags"] == [{"tagType": "style", "tagValue": "casual"}]


@pytest.mark.asyncio
async def test_get_product_variants_excludes_inactive(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    product = await _create_product(db_session)
    token = create_access_token(str(user.id))

    response = client.get(
        f"/api/v1/products/{product.id}/variants",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert len(response.json()["data"]) == 1


def test_get_unknown_product_is_404(client: TestClient) -> None:
    client.post("/api/v1/guest-sessions", json={})
    guest_token = client.post("/api/v1/guest-sessions", json={}).json()["data"]["guestToken"]
    response = client.get(
        f"/api/v1/products/{uuid4()}", headers={"Authorization": f"Bearer {guest_token}"}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


@pytest.mark.asyncio
async def test_viewing_product_records_recent_product(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    product = await _create_product(db_session)
    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}

    client.get(f"/api/v1/products/{product.id}", headers=headers)
    # viewing again should update, not duplicate
    client.get(f"/api/v1/products/{product.id}", headers=headers)

    response = client.get("/api/v1/recent-products", headers=headers)
    assert response.status_code == 200
    items = response.json()["data"]
    assert len(items) == 1
    assert items[0]["productId"] == str(product.id)
