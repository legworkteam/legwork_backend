from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.modules.stores.models import Campaign, QrCodeMapping, Store


async def _seed_qr(db_session, *, active: bool = True) -> tuple[Store, Campaign, QrCodeMapping]:
    store = Store(name="Test Store", address="Seoul", active=True)
    campaign = Campaign(name="Test Campaign", active=True)
    db_session.add_all([store, campaign])
    await db_session.commit()
    await db_session.refresh(store)
    await db_session.refresh(campaign)
    qr = QrCodeMapping(
        code=f"qr-{uuid4().hex[:8]}", store_id=store.id, campaign_id=campaign.id, active=active
    )
    db_session.add(qr)
    await db_session.commit()
    await db_session.refresh(qr)
    return store, campaign, qr


def test_guest_session_without_qr(client: TestClient) -> None:
    response = client.post("/api/v1/guest-sessions", json={})
    assert response.status_code == 201
    body = response.json()["data"]
    assert body["store"] is None
    assert body["campaign"] is None
    assert body["guestToken"]
    assert body["expiresAt"].endswith("+09:00")


@pytest.mark.asyncio
async def test_guest_session_with_valid_qr(db_session, client: TestClient) -> None:
    store, campaign, qr = await _seed_qr(db_session)
    response = client.post("/api/v1/guest-sessions", json={"qrCode": qr.code})
    assert response.status_code == 201
    body = response.json()["data"]
    assert body["store"]["name"] == store.name
    assert body["campaign"]["name"] == campaign.name


@pytest.mark.asyncio
async def test_guest_session_with_inactive_qr_is_invalid(db_session, client: TestClient) -> None:
    _, _, qr = await _seed_qr(db_session, active=False)
    response = client.post("/api/v1/guest-sessions", json={"qrCode": qr.code})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "QR_INVALID"


def test_guest_session_with_unknown_qr(client: TestClient) -> None:
    response = client.post("/api/v1/guest-sessions", json={"qrCode": "does-not-exist"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "QR_INVALID"
