from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.enums import AuthProvider, FileOwnerType
from app.core.security import create_access_token, create_guest_token
from app.modules.files.service import FileService
from app.modules.guests.models import GuestSession
from app.modules.users.models import User
from app.utils.datetime import now_kst


async def _create_user(db_session) -> User:
    user = User(
        name="File Owner",
        email=f"file-{uuid4().hex}@example.com",
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


@pytest.mark.asyncio
async def test_private_file_owner_can_download(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    service = FileService(db_session)
    created = await service.create_private_file(
        owner_type=FileOwnerType.USER,
        owner_id=user.id,
        filename="private.jpg",
        content_type="image/jpeg",
        content=b"\xff\xd8\xff\xe0private",
    )

    response = client.get(
        f"/api/v1/files/{created.id}",
        headers={"Authorization": f"Bearer {create_access_token(str(user.id))}"},
    )

    assert response.status_code == 200
    assert response.content == b"\xff\xd8\xff\xe0private"
    assert response.headers["content-type"].startswith("image/jpeg")
    assert "uploads/" not in response.text


@pytest.mark.asyncio
async def test_private_file_rejects_other_owner(db_session, client: TestClient) -> None:
    owner = await _create_guest_session(db_session)
    other_owner = await _create_guest_session(db_session)
    service = FileService(db_session)
    created = await service.create_private_file(
        owner_type=FileOwnerType.GUEST,
        owner_id=owner.id,
        filename="guest.png",
        content_type="image/png",
        content=b"\x89PNG\r\n\x1a\nguest",
    )

    response = client.get(
        f"/api/v1/files/{created.id}",
        headers={"Authorization": f"Bearer {create_guest_token(str(other_owner.id), other_owner.expires_at)}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
