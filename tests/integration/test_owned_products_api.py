from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.enums import AuthProvider
from app.core.security import create_access_token
from app.modules.products.models import Product, ProductCareGuide
from app.modules.users.models import User


async def _create_user(db_session, name: str = "OwnedMember") -> User:
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


async def _create_product(db_session, *, category: str = "bag", with_care_guide: bool = False) -> Product:
    product = Product(
        product_code=f"OWN-{uuid4().hex[:8]}",
        name="Owned Bag",
        category=category,
        base_price=400000,
        currency="KRW",
        active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    if with_care_guide:
        db_session.add(
            ProductCareGuide(
                product_id=product.id,
                title="전용 케어 가이드",
                guide_json={"material": "leather"},
                as_info_json={"warranty": "1year"},
            )
        )
        await db_session.commit()
    return product


@pytest.mark.asyncio
async def test_register_by_serial_then_duplicate_conflicts(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    product = await _create_product(db_session)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    first = client.post(
        "/api/v1/me/products",
        json={"serialNumber": product.product_code, "nickname": "My bag"},
        headers=headers,
    )
    assert first.status_code == 201
    body = first.json()["data"]
    assert body["source"] == "manual"
    assert body["nickname"] == "My bag"

    duplicate = client.post(
        "/api/v1/me/products", json={"serialNumber": product.product_code}, headers=headers
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ALREADY_REGISTERED"


def test_register_unknown_serial_is_404(client: TestClient) -> None:
    email = f"unkserial-{uuid4().hex}@example.com"
    client.post("/api/v1/auth/signup", json={"email": email, "password": "Abcd1234!", "name": "x"})
    token = client.post("/api/v1/auth/login", json={"email": email, "password": "Abcd1234!"}).json()[
        "data"
    ]["accessToken"]

    response = client.post(
        "/api/v1/me/products",
        json={"serialNumber": "NO-SUCH-SERIAL"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SERIAL_NOT_FOUND"


@pytest.mark.asyncio
async def test_care_guide_uses_product_specific_guide_when_present(
    db_session, client: TestClient
) -> None:
    user = await _create_user(db_session)
    product = await _create_product(db_session, with_care_guide=True)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    registered = client.post(
        "/api/v1/me/products", json={"serialNumber": product.product_code}, headers=headers
    ).json()["data"]

    guide = client.get(
        f"/api/v1/me/products/{registered['registrationId']}/care-guide", headers=headers
    )
    assert guide.status_code == 200
    body = guide.json()["data"]
    assert body["source"] == "product"
    assert body["title"] == "전용 케어 가이드"


@pytest.mark.asyncio
async def test_care_guide_falls_back_to_category_default(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    product = await _create_product(db_session, category="shoes", with_care_guide=False)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    registered = client.post(
        "/api/v1/me/products", json={"serialNumber": product.product_code}, headers=headers
    ).json()["data"]

    guide = client.get(
        f"/api/v1/me/products/{registered['registrationId']}/care-guide", headers=headers
    )
    assert guide.status_code == 200
    assert guide.json()["data"]["source"] == "categoryDefault"


@pytest.mark.asyncio
async def test_get_product_detail_and_list(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    product = await _create_product(db_session)
    headers = {"Authorization": f"Bearer {create_access_token(str(user.id))}"}

    registered = client.post(
        "/api/v1/me/products", json={"serialNumber": product.product_code}, headers=headers
    ).json()["data"]

    detail = client.get(f"/api/v1/me/products/{registered['registrationId']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["data"]["category"] == "bag"

    listed = client.get("/api/v1/me/products", headers=headers)
    assert len(listed.json()["data"]) == 1
