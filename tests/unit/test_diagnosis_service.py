from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.enums import (
    AuthProvider,
    DamageSeverity,
    DiagnosisProviderKind,
    FileOwnerType,
    JobType,
    RegisteredProductSource,
)
from app.modules.diagnoses.models import Diagnosis
from app.modules.diagnoses.service import DiagnosisService
from app.modules.files.service import FileService
from app.modules.jobs.service import JobService
from app.modules.owned_products.models import RegisteredProduct
from app.modules.owned_products.repository import RegisteredProductRepository
from app.modules.owned_products.service import OwnedProductService
from app.modules.products.models import Product, ProductCareGuide
from app.modules.products.repository import ProductRepository
from app.modules.users.models import User
from app.providers.diagnosis.base import (
    DiagnosisDamageResult,
    DiagnosisProviderRequest,
    DiagnosisProviderResult,
)
from app.storage.local import LocalStorageService


class StubDiagnosisProvider:
    def __init__(self) -> None:
        self.calls: list[DiagnosisProviderRequest] = []

    async def diagnose(self, payload: DiagnosisProviderRequest) -> DiagnosisProviderResult:
        self.calls.append(payload)
        return DiagnosisProviderResult(
            overall_condition="repairRecommended",
            repair_needed=True,
            summary="Deterministic unit-test diagnosis.",
            damages=[
                DiagnosisDamageResult(
                    damage_type="scratch",
                    area="corner",
                    severity=DamageSeverity.HIGH,
                    summary="Corner scratch.",
                    confidence=0.93,
                    repair_needed=True,
                )
            ],
            provider="mock",
        )


@pytest.mark.asyncio
async def test_diagnosis_service_processes_job_and_reads_care_guide(db_session, test_file_root: Path) -> None:
    user = User(
        name="DiagnosisSvc",
        email=f"diagnosis-{uuid4().hex}@example.com",
        auth_provider=AuthProvider.LOCAL,
        provider_user_id=None,
        password_hash="hash",
        phone=None,
        login_fail_count=0,
        locked_until=None,
        deleted_at=None,
    )
    product = Product(
        product_code="DEMO-BAG-001",
        name="Demo Bag",
        description="Diagnosis test product",
        category="bag",
        base_price=890000,
        currency="KRW",
        active=True,
    )
    db_session.add_all([user, product])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(product)

    db_session.add(
        ProductCareGuide(
            product_id=product.id,
            title="Demo care guide",
            guide_json={"tips": ["clean gently"]},
            as_info_json={"repair": "available"},
        )
    )
    registration = RegisteredProduct(
        user_id=user.id,
        product_id=product.id,
        order_item_id=None,
        serial_number="SERIAL-001",
        source=RegisteredProductSource.MANUAL,
        purchase_date=date(2026, 8, 1),
        nickname="My Demo",
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)

    storage = LocalStorageService(test_file_root)
    file_service = FileService(db_session, storage=storage)
    source_file = await file_service.create_private_file(
        owner_type=FileOwnerType.USER,
        owner_id=user.id,
        filename="damage.jpg",
        content_type="image/jpeg",
        content=b"\xff\xd8\xff\xe0diagnosis-source",
    )
    job = await JobService(db_session).create_job(
        principal=type("PrincipalObj", (), {"kind": "member", "user_id": user.id, "guest_session_id": None})(),
        job_type=JobType.DIAGNOSIS,
    )

    service = DiagnosisService(
        db_session,
        owned_product_service=OwnedProductService(
            RegisteredProductRepository(db_session),
            ProductRepository(db_session),
        ),
        provider=StubDiagnosisProvider(),
        storage=storage,
    )

    result = await service.process_job(
        job_id=job.id,
        user_id=user.id,
        registered_product_id=registration.id,
        source_file_id=source_file.id,
    )

    assert "diagnosisId" in result
    diagnosis = await db_session.get(Diagnosis, result["diagnosisId"])
    assert diagnosis is not None
    assert diagnosis.provider == DiagnosisProviderKind.MOCK

    detail = await service.get_diagnosis(user_id=user.id, diagnosis_id=diagnosis.id)
    assert detail.repair_needed is True
    assert detail.damages[0].severity == DamageSeverity.HIGH

    guide = await service.get_care_guide(user_id=user.id, diagnosis_id=diagnosis.id)
    assert guide.product_id == product.id
    assert guide.source == "product"
