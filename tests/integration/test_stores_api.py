from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.enums import AuthProvider
from app.core.security import create_access_token
from app.modules.stores.models import Store
from app.modules.users.models import User


async def _create_user(db_session, name: str = "StoreMember") -> User:
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


@pytest.mark.asyncio
async def test_list_stores_returns_active_stores_with_slots(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    db_session.add_all(
        [
            Store(name="Active Store", address="Seoul", active=True),
            Store(name="Inactive Store", address="Busan", active=False),
        ]
    )
    await db_session.commit()
    token = create_access_token(str(user.id))

    response = client.get(
        "/api/v1/stores",
        params={"date": "2026-09-01"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    stores = response.json()["data"]["stores"]
    names = [s["name"] for s in stores]
    assert "Active Store" in names
    assert "Inactive Store" not in names
    active = next(s for s in stores if s["name"] == "Active Store")
    assert len(active["availableSlots"]) == 8
    assert active["availableSlots"][0].startswith("2026-09-01T11:00:00")


def test_list_stores_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/stores")
    assert response.status_code == 401
