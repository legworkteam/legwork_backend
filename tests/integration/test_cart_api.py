from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.enums import AuthProvider
from app.core.security import create_access_token
from app.modules.products.models import Product, ProductVariant
from app.modules.users.models import User


async def _create_user(db_session, name: str = "CartMember") -> User:
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


async def _create_product_with_variants(db_session) -> tuple[Product, ProductVariant, ProductVariant]:
    product = Product(
        product_code=f"CART-{uuid4().hex[:8]}",
        name="Cart Bag",
        category="bag",
        base_price=300000,
        currency="KRW",
        active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    v1 = ProductVariant(
        product_id=product.id, sku=f"{product.product_code}-BLK",
        color="black", size="M", price=300000, stock=3, active=True,
    )
    v2 = ProductVariant(
        product_id=product.id, sku=f"{product.product_code}-OFF",
        color="red", size="S", price=1, stock=9, active=False,
    )
    db_session.add_all([v1, v2])
    await db_session.commit()
    await db_session.refresh(v1)
    await db_session.refresh(v2)
    return product, v1, v2


@pytest.mark.asyncio
async def test_add_item_then_add_again_merges_quantity(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    _, variant, _ = await _create_product_with_variants(db_session)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    first = client.post(
        "/api/v1/cart/items", json={"variantId": str(variant.id), "quantity": 2}, headers=headers
    )
    assert first.status_code == 201
    assert first.json()["data"]["totalAmount"] == 600000

    second = client.post(
        "/api/v1/cart/items", json={"variantId": str(variant.id), "quantity": 1}, headers=headers
    )
    body = second.json()["data"]
    assert len(body["items"]) == 1
    assert body["items"][0]["quantity"] == 3
    assert body["totalAmount"] == 900000


@pytest.mark.asyncio
async def test_add_item_over_stock_is_conflict(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    _, variant, _ = await _create_product_with_variants(db_session)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    response = client.post(
        "/api/v1/cart/items", json={"variantId": str(variant.id), "quantity": 5}, headers=headers
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INSUFFICIENT_STOCK"


@pytest.mark.asyncio
async def test_add_inactive_variant_is_conflict(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    _, _, inactive_variant = await _create_product_with_variants(db_session)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    response = client.post(
        "/api/v1/cart/items",
        json={"variantId": str(inactive_variant.id), "quantity": 1},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "VARIANT_UNAVAILABLE"


def test_add_unknown_variant_is_404(client: TestClient) -> None:
    email = f"unknownvariant-{uuid4().hex}@example.com"
    client.post("/api/v1/auth/signup", json={"email": email, "password": "Abcd1234!", "name": "x"})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": "Abcd1234!"}).json()[
        "data"
    ]["accessToken"]

    response = client.post(
        "/api/v1/cart/items",
        json={"variantId": str(uuid4()), "quantity": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "VARIANT_NOT_FOUND"


@pytest.mark.asyncio
async def test_update_and_delete_cart_item(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    _, variant, _ = await _create_product_with_variants(db_session)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    add = client.post(
        "/api/v1/cart/items", json={"variantId": str(variant.id), "quantity": 2}, headers=headers
    )
    item_id = add.json()["data"]["items"][0]["cartItemId"]

    updated = client.patch(
        f"/api/v1/cart/items/{item_id}", json={"quantity": 1}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["totalAmount"] == 300000

    deleted = client.delete(f"/api/v1/cart/items/{item_id}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json()["data"]["items"] == []

    fetched = client.get("/api/v1/cart", headers=headers)
    assert fetched.json()["data"]["items"] == []


def test_cart_endpoints_require_member_auth(client: TestClient) -> None:
    assert client.get("/api/v1/cart").status_code == 401
    assert client.post("/api/v1/cart/items", json={"variantId": str(uuid4()), "quantity": 1}).status_code == 401
