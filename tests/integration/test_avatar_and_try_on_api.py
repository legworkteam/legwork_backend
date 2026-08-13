from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.enums import AuthProvider, Gender, JobStatus, TryOnScope
from app.core.security import create_access_token, create_guest_token
from app.modules.avatars.models import Avatar
from app.modules.files.models import FileMetadata
from app.modules.guests.models import GuestSession
from app.modules.products.models import Product
from app.modules.try_on.models import TryOn
from app.modules.try_on.router import get_try_on_provider
from app.modules.users.models import User
from app.providers.try_on.base import TryOnAvatarParameters, TryOnProviderRequest, TryOnProviderResult
from app.utils.datetime import now_kst


JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"jpeg-content"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"png-content"
WEBP_BYTES = b"RIFF1234WEBP" + b"webp-content"


class StubTryOnProvider:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[TryOnProviderRequest] = []

    async def generate(self, payload: TryOnProviderRequest) -> TryOnProviderResult:
        self.calls.append(payload)
        if self.fail or payload.simulate_failure:
            from app.core.exceptions import GenerationFailedError

            raise GenerationFailedError("Stub failure.")
        return TryOnProviderResult(
            filename="result.png",
            content_type="image/png",
            content=PNG_BYTES,
            provider="mock",
        )


async def _create_user(db_session, name: str = "Member") -> User:
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


async def _create_guest_session(db_session) -> GuestSession:
    guest = GuestSession(
        expires_at=now_kst() + timedelta(hours=2),
        qr_code_id=None,
        height_cm=None,
        weight_kg=None,
        gender=None,
        photo_try_on_count=0,
    )
    db_session.add(guest)
    await db_session.commit()
    await db_session.refresh(guest)
    return guest


async def _create_product(db_session, code: str = "DEMO-BAG-001") -> Product:
    product = Product(
        product_code=code,
        name="Demo Bag",
        description="Try-on test product",
        category="bag",
        base_price=890000,
        currency="KRW",
        active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.mark.asyncio
async def test_avatar_create_get_update_member(db_session, client: TestClient) -> None:
    user = await _create_user(db_session, "AvatarMember")
    token = create_access_token(str(user.id))

    create_response = client.post(
        "/api/v1/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        json={"heightCm": 172, "weightKg": 65, "gender": "female"},
    )
    assert create_response.status_code == 201
    assert create_response.json()["data"]["gender"] == "female"

    get_response = client.get(
        "/api/v1/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"]["heightCm"] == 172

    put_response = client.put(
        "/api/v1/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        json={"heightCm": 175, "weightKg": 66, "gender": "neutral"},
    )
    assert put_response.status_code == 200
    assert put_response.json()["data"]["gender"] == "neutral"


@pytest.mark.asyncio
async def test_avatar_rejects_duplicate_create_and_invalid_values(db_session, client: TestClient) -> None:
    user = await _create_user(db_session, "DupMember")
    token = create_access_token(str(user.id))

    first = client.post(
        "/api/v1/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        json={"heightCm": 172, "weightKg": 65, "gender": "female"},
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        json={"heightCm": 172, "weightKg": 65, "gender": "female"},
    )
    assert duplicate.status_code == 409

    invalid = client.post(
        "/api/v1/me/avatar",
        headers={"Authorization": f"Bearer {token}"},
        json={"heightCm": 99, "weightKg": 20, "gender": "female"},
    )
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_guest_avatar_parameters_are_saved_on_guest_session(db_session, client: TestClient) -> None:
    guest = await _create_guest_session(db_session)
    token = create_guest_token(str(guest.id), guest.expires_at)

    response = client.put(
        "/api/v1/guest-sessions/me/avatar-parameters",
        headers={"Authorization": f"Bearer {token}"},
        json={"heightCm": 168, "weightKg": 58, "gender": "male"},
    )

    assert response.status_code == 200
    await db_session.refresh(guest)
    assert float(guest.height_cm) == 168
    assert float(guest.weight_kg) == 58
    assert guest.gender == Gender.MALE


@pytest.mark.asyncio
async def test_avatar_try_on_guest_default_and_member_avatar(db_session, client: TestClient) -> None:
    product = await _create_product(db_session)
    guest = await _create_guest_session(db_session)
    member = await _create_user(db_session, "TryOnMember")
    db_session.add(
        Avatar(
            user_id=member.id,
            height_cm=181,
            weight_kg=72,
            gender=Gender.FEMALE,
            preview_file_id=None,
        )
    )
    await db_session.commit()

    stub = StubTryOnProvider()
    client.app.dependency_overrides[get_try_on_provider] = lambda: stub

    guest_response = client.post(
        "/api/v1/avatar-try-ons",
        headers={"Authorization": f"Bearer {create_guest_token(str(guest.id), guest.expires_at)}"},
        json={"scope": "productOnly", "productId": str(product.id)},
    )
    assert guest_response.status_code == 202
    assert stub.calls[-1].avatar == TryOnAvatarParameters(170.0, 65.0, Gender.NEUTRAL)

    member_response = client.post(
        "/api/v1/avatar-try-ons",
        headers={"Authorization": f"Bearer {create_access_token(str(member.id))}"},
        json={"scope": "productOnly", "productId": str(product.id)},
    )
    assert member_response.status_code == 202
    assert stub.calls[-1].avatar == TryOnAvatarParameters(181.0, 72.0, Gender.FEMALE)

    client.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_avatar_try_on_job_failed_when_product_missing(db_session, client: TestClient) -> None:
    guest = await _create_guest_session(db_session)
    stub = StubTryOnProvider()
    client.app.dependency_overrides[get_try_on_provider] = lambda: stub

    response = client.post(
        "/api/v1/avatar-try-ons",
        headers={"Authorization": f"Bearer {create_guest_token(str(guest.id), guest.expires_at)}"},
        json={"scope": "productOnly", "productId": str(uuid4())},
    )
    assert response.status_code == 202

    job_response = client.get(
        f"/api/v1/jobs/{response.json()['data']['jobId']}",
        headers={"Authorization": f"Bearer {create_guest_token(str(guest.id), guest.expires_at)}"},
    )
    assert job_response.status_code == 200
    assert job_response.json()["data"]["status"] == JobStatus.FAILED.value
    assert job_response.json()["data"]["error"]["code"] == "PRODUCT_NOT_FOUND"
    client.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_photo_try_on_guest_limit_and_validation(db_session, client: TestClient) -> None:
    product = await _create_product(db_session)
    guest = await _create_guest_session(db_session)
    token = create_guest_token(str(guest.id), guest.expires_at)
    stub = StubTryOnProvider()
    client.app.dependency_overrides[get_try_on_provider] = lambda: stub

    for _ in range(3):
        response = client.post(
            "/api/v1/try-ons",
            headers={"Authorization": f"Bearer {token}"},
            data={"scope": "productOnly", "productId": str(product.id)},
            files={"photo": ("person.jpg", JPEG_BYTES, "image/jpeg")},
        )
        assert response.status_code == 202

    fourth = client.post(
        "/api/v1/try-ons",
        headers={"Authorization": f"Bearer {token}"},
        data={"scope": "productOnly", "productId": str(product.id)},
        files={"photo": ("person.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert fourth.status_code == 429
    assert fourth.json()["error"]["code"] == "GUEST_LIMIT_EXCEEDED"

    fresh_guest = await _create_guest_session(db_session)
    invalid = client.post(
        "/api/v1/try-ons",
        headers={"Authorization": f"Bearer {create_guest_token(str(fresh_guest.id), fresh_guest.expires_at)}"},
        data={"scope": "productOnly", "productId": str(product.id)},
        files={"photo": ("person.png", b"not-a-real-png", "image/png")},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    client.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_photo_try_on_save_list_delete_and_ttl(db_session, client: TestClient, test_file_root: Path) -> None:
    product = await _create_product(db_session)
    user = await _create_user(db_session, "SaveMember")
    user_id = user.id
    token = create_access_token(str(user.id))
    stub = StubTryOnProvider()
    client.app.dependency_overrides[get_try_on_provider] = lambda: stub

    create_response = client.post(
        "/api/v1/try-ons",
        headers={"Authorization": f"Bearer {token}"},
        data={"scope": "productOnly", "productId": str(product.id)},
        files={"photo": ("person.webp", WEBP_BYTES, "image/webp")},
    )
    assert create_response.status_code == 202
    job_id = create_response.json()["data"]["jobId"]

    job_response = client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert job_response.status_code == 200
    result = job_response.json()["data"]["result"]
    try_on_id = result["tryOnId"]
    result_file_id = result["resultFileId"]

    result_scalars = await db_session.scalars(select(FileMetadata))
    source_files = list(result_scalars.all())
    assert len(source_files) >= 2
    source_file = next(row for row in source_files if row.id != UUID(result_file_id))
    result_file = next(row for row in source_files if row.id == UUID(result_file_id))
    source_file_id = source_file.id
    assert source_file.expires_at is not None
    assert result_file.expires_at is not None

    save_response = client.post(
        f"/api/v1/try-ons/{try_on_id}/save",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert save_response.status_code == 200
    assert save_response.json()["data"]["expiresAt"] is None

    db_session.expire_all()
    saved_result_file = await db_session.get(FileMetadata, UUID(result_file_id))
    saved_source_file = await db_session.get(FileMetadata, source_file_id)
    assert saved_result_file.expires_at is None
    assert saved_source_file.expires_at is not None

    list_response = client.get(
        "/api/v1/me/try-ons",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    file_response = client.get(
        f"/api/v1/files/{result_file_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert file_response.status_code == 200
    assert file_response.content == PNG_BYTES

    delete_response = client.delete(
        f"/api/v1/me/try-ons/{try_on_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 200
    assert not list((test_file_root / "uploads" / "members" / str(user_id)).glob("*.png"))

    other_user = await _create_user(db_session, "OtherMember")
    forbidden = client.post(
        f"/api/v1/try-ons/{try_on_id}/save",
        headers={"Authorization": f"Bearer {create_access_token(str(other_user.id))}"},
    )
    assert forbidden.status_code in {403, 404}

    client.app.dependency_overrides.clear()
