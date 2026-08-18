from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_guest_token
from app.modules.guests.models import GuestSession
from app.modules.products.models import Product, RecentProduct
from app.utils.datetime import now_kst

PASSWORD = "Abcd1234!"


def _signup(client: TestClient, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": PASSWORD, "name": "Tester"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def test_signup_then_duplicate_email_conflicts(client: TestClient) -> None:
    email = f"dup-{uuid4().hex}@example.com"
    _signup(client, email)
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": PASSWORD, "name": "Again"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


def test_signup_rejects_weak_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": f"weak-{uuid4().hex}@example.com", "password": "weak", "name": "x"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_login_success_returns_token_expiry_values(client: TestClient) -> None:
    email = f"login-{uuid4().hex}@example.com"
    _signup(client, email)
    response = _login(client, email)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["accessTokenExpiresIn"] == 7200
    assert data["refreshTokenExpiresIn"] == 1209600
    assert data["accessToken"] and data["refreshToken"]


def test_login_wrong_password_then_lockout_after_five_failures(client: TestClient) -> None:
    email = f"lock-{uuid4().hex}@example.com"
    _signup(client, email)

    for _ in range(4):
        response = _login(client, email, password="WrongPass1!")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"

    fifth = _login(client, email, password="WrongPass1!")
    assert fifth.status_code == 429
    assert fifth.json()["error"]["code"] == "LOGIN_TEMPORARILY_LOCKED"

    # still locked even with the correct password
    sixth = _login(client, email)
    assert sixth.status_code == 429
    assert sixth.json()["error"]["code"] == "LOGIN_TEMPORARILY_LOCKED"


def test_refresh_rotates_and_revokes_old_token(client: TestClient) -> None:
    email = f"refresh-{uuid4().hex}@example.com"
    _signup(client, email)
    tokens = _login(client, email).json()["data"]
    old_refresh = tokens["refreshToken"]

    rotated = client.post("/api/v1/auth/refresh", json={"refreshToken": old_refresh})
    assert rotated.status_code == 200
    new_refresh = rotated.json()["data"]["refreshToken"]
    assert new_refresh != old_refresh

    reused = client.post("/api/v1/auth/refresh", json={"refreshToken": old_refresh})
    assert reused.status_code == 401


def test_logout_revokes_refresh_token(client: TestClient) -> None:
    email = f"logout-{uuid4().hex}@example.com"
    _signup(client, email)
    tokens = _login(client, email).json()["data"]

    logout = client.post(
        "/api/v1/auth/logout",
        json={"refreshToken": tokens["refreshToken"]},
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
    )
    assert logout.status_code == 200

    refreshed = client.post("/api/v1/auth/refresh", json={"refreshToken": tokens["refreshToken"]})
    assert refreshed.status_code == 401


def test_logout_requires_member_auth(client: TestClient) -> None:
    response = client.post("/api/v1/auth/logout", json={"refreshToken": "whatever"})
    assert response.status_code == 401


def test_social_login_is_idempotent_and_separates_providers(client: TestClient) -> None:
    code = uuid4().hex
    first = client.post(
        "/api/v1/auth/social", json={"provider": "google", "authorizationCode": code}
    )
    assert first.status_code == 200
    user_id = first.json()["data"]["userId"]

    same_code_again = client.post(
        "/api/v1/auth/social", json={"provider": "google", "authorizationCode": code}
    )
    assert same_code_again.json()["data"]["userId"] == user_id

    other_provider = client.post(
        "/api/v1/auth/social", json={"provider": "kakao", "authorizationCode": code}
    )
    assert other_provider.status_code == 200
    assert other_provider.json()["data"]["userId"] != user_id


def test_social_login_rejects_unknown_provider(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/social",
        json={"provider": "naver", "authorizationCode": "x"},
    )
    assert response.status_code == 422


async def _create_product(db_session, code: str) -> Product:
    product = Product(
        product_code=code,
        name=f"Claim Product {code}",
        category="bag",
        base_price=100000,
        currency="KRW",
        active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.mark.asyncio
async def test_claim_migrates_guest_recent_products_and_merges_overlap(
    db_session, client: TestClient
) -> None:
    product_a = await _create_product(db_session, f"CLAIM-A-{uuid4().hex[:6]}")
    product_b = await _create_product(db_session, f"CLAIM-B-{uuid4().hex[:6]}")

    guest = GuestSession(expires_at=now_kst() + timedelta(hours=1))
    db_session.add(guest)
    await db_session.commit()
    await db_session.refresh(guest)
    guest_token = create_guest_token(str(guest.id), guest.expires_at)

    db_session.add_all(
        [
            RecentProduct(product_id=product_a.id, guest_session_id=guest.id, viewed_at=now_kst()),
            RecentProduct(product_id=product_b.id, guest_session_id=guest.id, viewed_at=now_kst()),
        ]
    )
    await db_session.commit()

    email = f"claim-{uuid4().hex}@example.com"
    _signup(client, email)
    tokens = _login(client, email).json()["data"]
    member_headers = {"Authorization": f"Bearer {tokens['accessToken']}"}

    # member already viewed product_a before claiming -> should merge, not duplicate
    client.get(f"/api/v1/products/{product_a.id}", headers=member_headers)

    claim = client.post(
        "/api/v1/auth/claim", json={"guestToken": guest_token}, headers=member_headers
    )
    assert claim.status_code == 200
    assert claim.json()["data"]["recentProductsClaimed"] == 2

    member_recent = client.get("/api/v1/recent-products", headers=member_headers)
    product_ids = {item["productId"] for item in member_recent.json()["data"]}
    assert product_ids == {str(product_a.id), str(product_b.id)}

    guest_recent = client.get(
        "/api/v1/recent-products", headers={"Authorization": f"Bearer {guest_token}"}
    )
    assert guest_recent.json()["data"] == []


def test_claim_rejects_invalid_guest_token(client: TestClient) -> None:
    email = f"claimbad-{uuid4().hex}@example.com"
    _signup(client, email)
    tokens = _login(client, email).json()["data"]
    response = client.post(
        "/api/v1/auth/claim",
        json={"guestToken": "not-a-real-token"},
        headers={"Authorization": f"Bearer {tokens['accessToken']}"},
    )
    assert response.status_code == 401
