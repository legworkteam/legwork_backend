from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.enums import AuthProvider, DamageSeverity, RegisteredProductSource
from app.core.security import create_access_token
from app.modules.diagnoses.router import get_diagnosis_provider
from app.modules.owned_products.models import RegisteredProduct
from app.modules.products.models import Product, ProductCareGuide
from app.modules.stores.models import Store
from app.modules.users.models import User
from app.providers.diagnosis.base import (
    DiagnosisDamageResult,
    DiagnosisProviderRequest,
    DiagnosisProviderResult,
)


JPEG_BYTES = b"\xff\xd8\xff\xe0diagnosis-jpeg"


class StubDiagnosisProvider:
    def __init__(self, *, repair_needed: bool = True, fail: bool = False) -> None:
        self.repair_needed = repair_needed
        self.fail = fail
        self.calls: list[DiagnosisProviderRequest] = []

    async def diagnose(self, payload: DiagnosisProviderRequest) -> DiagnosisProviderResult:
        self.calls.append(payload)
        if self.fail or payload.simulate_failure:
            from app.core.exceptions import ProviderError

            raise ProviderError("Stub diagnosis failure.")
        return DiagnosisProviderResult(
            overall_condition="repairRecommended" if self.repair_needed else "good",
            repair_needed=self.repair_needed,
            summary="Stub diagnosis result.",
            damages=[
                DiagnosisDamageResult(
                    damage_type="scratch",
                    area="corner",
                    severity=DamageSeverity.HIGH if self.repair_needed else DamageSeverity.LOW,
                    summary="Stub corner scratch.",
                    confidence=0.95,
                    repair_needed=self.repair_needed,
                )
            ],
            provider="mock",
        )


async def _create_user(db_session, name: str) -> User:
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


async def _create_registered_product(db_session, user_id) -> RegisteredProduct:
    product = Product(
        product_code=f"DEMO-BAG-{uuid4().hex[:4]}",
        name="Diagnosis Demo Bag",
        description="Integration diagnosis product",
        category="bag",
        base_price=790000,
        currency="KRW",
        active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    db_session.add(
        ProductCareGuide(
            product_id=product.id,
            title="Diagnosis guide",
            guide_json={"tips": ["keep dry"]},
            as_info_json={"repair": "available"},
        )
    )
    registration = RegisteredProduct(
        user_id=user_id,
        product_id=product.id,
        order_item_id=None,
        serial_number=f"SERIAL-{uuid4().hex[:6]}",
        source=RegisteredProductSource.MANUAL,
        purchase_date=date(2026, 8, 1),
        nickname="Owned bag",
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)
    return registration


async def _create_store(db_session, name: str = "Repair Store") -> Store:
    store = Store(name=name, address="Seoul", phone="02-0000-0000", active=True)
    db_session.add(store)
    await db_session.commit()
    await db_session.refresh(store)
    return store


@pytest.mark.asyncio
async def test_diagnosis_job_polling_detail_care_guide_and_repair_flow(
    db_session,
    client: TestClient,
) -> None:
    user = await _create_user(db_session, "DiagnosisMember")
    registration = await _create_registered_product(db_session, user.id)
    store = await _create_store(db_session)
    token = create_access_token(str(user.id))
    stub = StubDiagnosisProvider(repair_needed=True)
    client.app.dependency_overrides[get_diagnosis_provider] = lambda: stub

    create_response = client.post(
        "/api/v1/diagnoses",
        headers={"Authorization": f"Bearer {token}"},
        data={"registeredProductId": str(registration.id)},
        files={"image": ("damage.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert create_response.status_code == 202
    job_id = create_response.json()["data"]["jobId"]

    job_response = client.get(
        f"/api/v1/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert job_response.status_code == 200
    assert job_response.json()["data"]["status"] == "succeeded"
    diagnosis_id = job_response.json()["data"]["result"]["diagnosisId"]

    diagnosis_response = client.get(
        f"/api/v1/diagnoses/{diagnosis_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert diagnosis_response.status_code == 200
    assert diagnosis_response.json()["data"]["repairNeeded"] is True
    assert diagnosis_response.json()["data"]["damages"][0]["damageType"] == "scratch"

    guide_response = client.get(
        f"/api/v1/diagnoses/{diagnosis_id}/care-guide",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert guide_response.status_code == 200
    assert guide_response.json()["data"]["productId"] == str(registration.product_id)

    slot = (datetime(2026, 8, 13, 13, 0) + timedelta(hours=1)).astimezone()
    reservation_response = client.post(
        "/api/v1/repair-reservations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "diagnosisId": diagnosis_id,
            "storeId": str(store.id),
            "slot": slot.isoformat(),
            "note": "please inspect the corner",
        },
    )
    assert reservation_response.status_code == 201
    reservation_id = reservation_response.json()["data"]["repairReservationId"]

    duplicate_response = client.post(
        "/api/v1/repair-reservations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "diagnosisId": diagnosis_id,
            "storeId": str(store.id),
            "slot": slot.isoformat(),
        },
    )
    assert duplicate_response.status_code == 409
    assert duplicate_response.json()["error"]["code"] == "REPAIR_SLOT_UNAVAILABLE"

    list_response = client.get(
        "/api/v1/repair-reservations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    cancel_response = client.post(
        f"/api/v1/repair-reservations/{reservation_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cancel_response.status_code == 200
    assert cancel_response.json()["data"]["status"] == "cancelled"

    client.app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_diagnosis_failure_and_repair_not_needed(db_session, client: TestClient) -> None:
    user = await _create_user(db_session, "DiagnosisFail")
    registration = await _create_registered_product(db_session, user.id)
    store = await _create_store(db_session, "Repair Store 2")
    token = create_access_token(str(user.id))

    failing_stub = StubDiagnosisProvider(fail=True)
    client.app.dependency_overrides[get_diagnosis_provider] = lambda: failing_stub
    failed_response = client.post(
        "/api/v1/diagnoses",
        headers={"Authorization": f"Bearer {token}"},
        data={"registeredProductId": str(registration.id)},
        files={"image": ("damage.jpg", JPEG_BYTES, "image/jpeg")},
    )
    assert failed_response.status_code == 202
    failed_job_id = failed_response.json()["data"]["jobId"]
    failed_job = client.get(
        f"/api/v1/jobs/{failed_job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert failed_job.status_code == 200
    assert failed_job.json()["data"]["status"] == "failed"
    assert failed_job.json()["data"]["error"]["code"] == "AI_UNAVAILABLE"

    no_repair_stub = StubDiagnosisProvider(repair_needed=False)
    client.app.dependency_overrides[get_diagnosis_provider] = lambda: no_repair_stub
    succeeded_response = client.post(
        "/api/v1/diagnoses",
        headers={"Authorization": f"Bearer {token}"},
        data={"registeredProductId": str(registration.id)},
        files={"image": ("damage.jpg", JPEG_BYTES, "image/jpeg")},
    )
    diagnosis_job_id = succeeded_response.json()["data"]["jobId"]
    job_response = client.get(
        f"/api/v1/jobs/{diagnosis_job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    diagnosis_id = job_response.json()["data"]["result"]["diagnosisId"]

    repair_response = client.post(
        "/api/v1/repair-reservations",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "diagnosisId": diagnosis_id,
            "storeId": str(store.id),
            "slot": datetime(2026, 8, 13, 15, 0).astimezone().isoformat(),
        },
    )
    assert repair_response.status_code == 422
    assert repair_response.json()["error"]["code"] == "REPAIR_NOT_NEEDED"

    client.app.dependency_overrides.clear()


def test_diagnosis_and_repairs_are_exposed_in_openapi(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/diagnoses" in paths
    assert "/api/v1/diagnoses/{diagnosisId}" in paths
    assert "/api/v1/diagnoses/{diagnosisId}/care-guide" in paths
    assert "/api/v1/repair-reservations" in paths
