from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.enums import AuthProvider
from app.core.security import create_access_token
from app.modules.owned_products.models import RegisteredProduct
from app.modules.products.models import Product, ProductVariant
from app.modules.users.models import User


async def _create_user(db_session, name: str = "OrderMember") -> User:
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


async def _create_variant(db_session, *, price: int, stock: int = 5) -> ProductVariant:
    product = Product(
        product_code=f"ORD-{uuid4().hex[:8]}",
        name="Order Wallet",
        category="wallet",
        base_price=price,
        currency="KRW",
        active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    variant = ProductVariant(
        product_id=product.id, sku=f"{product.product_code}-F",
        color="black", size="F", price=price, stock=stock, active=True,
    )
    db_session.add(variant)
    await db_session.commit()
    await db_session.refresh(variant)
    return variant


def _add_to_cart(client: TestClient, headers: dict, variant_id, quantity: int = 1) -> str:
    cart = client.post(
        "/api/v1/cart/items",
        json={"variantId": str(variant_id), "quantity": quantity},
        headers=headers,
    ).json()["data"]
    return next(i for i in cart["items"] if i["variantId"] == str(variant_id))["cartItemId"]


@pytest.mark.asyncio
async def test_order_success_decrements_stock_clears_cart_and_registers_product(
    db_session, client: TestClient
) -> None:
    user = await _create_user(db_session)
    variant = await _create_variant(db_session, price=200000, stock=5)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    item_id = _add_to_cart(client, headers, variant.id, quantity=2)

    response = client.post(
        "/api/v1/orders", json={"cartItemIds": [item_id]}, headers=headers
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["orderStatus"] == "paid"
    assert data["paymentStatus"] == "success"
    assert data["paidAmount"] == 400000
    order_id = data["orderId"]

    await db_session.refresh(variant)
    assert variant.stock == 3

    cart = client.get("/api/v1/cart", headers=headers)
    assert cart.json()["data"]["items"] == []

    registered = (
        await db_session.scalars(
            select(RegisteredProduct).where(RegisteredProduct.user_id == user.id)
        )
    ).all()
    assert len(registered) == 1
    assert str(registered[0].source) == "purchase" or registered[0].source.value == "purchase"

    detail = client.get(f"/api/v1/me/orders/{order_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["items"][0]["quantity"] == 2

    listed = client.get("/api/v1/me/orders", headers=headers)
    assert len(listed.json()["data"]) == 1


@pytest.mark.asyncio
async def test_order_decline_has_no_side_effects(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    variant = await _create_variant(db_session, price=13, stock=4)  # 13 triggers mock decline
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}
    item_id = _add_to_cart(client, headers, variant.id, quantity=1)

    response = client.post(
        "/api/v1/orders", json={"cartItemIds": [item_id]}, headers=headers
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["orderStatus"] == "failed"
    assert data["paymentStatus"] == "failed"
    assert data["paidAmount"] is None

    await db_session.refresh(variant)
    assert variant.stock == 4  # unchanged

    cart = client.get("/api/v1/cart", headers=headers)
    assert len(cart.json()["data"]["items"]) == 1  # untouched

    # the failed order is still retrievable
    detail = client.get(f"/api/v1/me/orders/{data['orderId']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["orderStatus"] == "failed"


@pytest.mark.asyncio
async def test_order_with_missing_cart_item_is_404(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    response = client.post(
        "/api/v1/orders", json={"cartItemIds": [str(uuid4())]}, headers=headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_cannot_view_another_users_order(db_session, client: TestClient) -> None:
    owner = await _create_user(db_session, "OrderOwner")
    stranger = await _create_user(db_session, "OrderStranger")
    variant = await _create_variant(db_session, price=100000, stock=5)
    owner_headers = {"Authorization": f"Bearer {create_access_token(str(owner.id))}"}
    item_id = _add_to_cart(client, owner_headers, variant.id)
    order = client.post(
        "/api/v1/orders", json={"cartItemIds": [item_id]}, headers=owner_headers
    ).json()["data"]

    stranger_headers = {"Authorization": f"Bearer {create_access_token(str(stranger.id))}"}
    response = client.get(f"/api/v1/me/orders/{order['orderId']}", headers=stranger_headers)
    assert response.status_code == 404
