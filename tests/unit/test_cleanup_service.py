from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.core.enums import (
    AuthProvider,
    DiagnosisProviderKind,
    FileOwnerType,
    FileVisibility,
    JobStatus,
    JobType,
    RegisteredProductSource,
    TryOnProviderKind,
    TryOnScope,
)
from app.modules.diagnoses.models import Diagnosis
from app.modules.files.models import FileMetadata
from app.modules.guests.models import GuestSession
from app.modules.jobs.models import Job
from app.modules.owned_products.models import RegisteredProduct
from app.modules.products.models import Product
from app.modules.try_on.models import TryOn
from app.modules.users.models import User
from app.storage.local import LocalStorageService
from app.tasks.cleanup import CleanupService
from app.utils.datetime import now_kst


@pytest.mark.asyncio
async def test_cleanup_service_removes_expired_resources_but_keeps_linked_jobs(
    db_session,
    test_file_root: Path,
) -> None:
    now = now_kst()
    storage = LocalStorageService(test_file_root)

    user = User(
        name="CleanupMember",
        email=f"cleanup-{uuid4().hex}@example.com",
        auth_provider=AuthProvider.LOCAL,
        provider_user_id=None,
        password_hash="hash",
        phone=None,
        login_fail_count=0,
        locked_until=None,
        deleted_at=None,
    )
    guest = GuestSession(
        expires_at=now - timedelta(minutes=10),
        qr_code_id=None,
        height_cm=None,
        weight_kg=None,
        gender=None,
        photo_try_on_count=0,
    )
    product = Product(
        product_code="DEMO-BAG-002",
        name="Cleanup Product",
        description=None,
        category="bag",
        base_price=1000,
        currency="KRW",
        active=True,
    )
    db_session.add_all([user, guest, product])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(guest)
    await db_session.refresh(product)

    registration = RegisteredProduct(
        user_id=user.id,
        product_id=product.id,
        order_item_id=None,
        serial_number="CLEAN-001",
        source=RegisteredProductSource.MANUAL,
        purchase_date=None,
        nickname=None,
    )
    db_session.add(registration)
    await db_session.commit()
    await db_session.refresh(registration)

    orphan_job = Job(
        user_id=user.id,
        guest_session_id=None,
        type=JobType.DIAGNOSIS,
        status=JobStatus.FAILED,
        progress=100,
        result_json=None,
        error_json={"code": "TEST"},
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(days=2),
        expires_at=now - timedelta(minutes=5),
    )
    try_on_job = Job(
        user_id=user.id,
        guest_session_id=None,
        type=JobType.PHOTO_TRY_ON,
        status=JobStatus.SUCCEEDED,
        progress=100,
        result_json=None,
        error_json=None,
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(days=2),
        expires_at=now - timedelta(minutes=5),
    )
    linked_diagnosis_job = Job(
        user_id=user.id,
        guest_session_id=None,
        type=JobType.DIAGNOSIS,
        status=JobStatus.SUCCEEDED,
        progress=100,
        result_json=None,
        error_json=None,
        created_at=now - timedelta(days=2),
        updated_at=now - timedelta(days=2),
        expires_at=now - timedelta(minutes=5),
    )
    db_session.add_all([orphan_job, try_on_job, linked_diagnosis_job])
    await db_session.commit()
    await db_session.refresh(orphan_job)
    await db_session.refresh(try_on_job)
    await db_session.refresh(linked_diagnosis_job)

    generic_file_path = "cleanup/generic-source.jpg"
    try_on_file_path = "cleanup/tryon-result.png"
    linked_diag_file_path = "cleanup/diagnosis-source.jpg"
    await storage.save(relative_path=generic_file_path, content=b"generic")
    await storage.save(relative_path=try_on_file_path, content=b"tryon")
    await storage.save(relative_path=linked_diag_file_path, content=b"diagnosis")

    generic_file = FileMetadata(
        owner_type=FileOwnerType.USER,
        owner_id=user.id,
        path=generic_file_path,
        original_name="generic-source.jpg",
        content_type="image/jpeg",
        size=7,
        visibility=FileVisibility.PRIVATE,
        expires_at=now - timedelta(minutes=1),
        created_at=now - timedelta(days=1),
    )
    try_on_file = FileMetadata(
        owner_type=FileOwnerType.USER,
        owner_id=user.id,
        path=try_on_file_path,
        original_name="tryon-result.png",
        content_type="image/png",
        size=5,
        visibility=FileVisibility.PRIVATE,
        expires_at=now - timedelta(minutes=1),
        created_at=now - timedelta(days=1),
    )
    linked_diag_file = FileMetadata(
        owner_type=FileOwnerType.USER,
        owner_id=user.id,
        path=linked_diag_file_path,
        original_name="diagnosis-source.jpg",
        content_type="image/jpeg",
        size=9,
        visibility=FileVisibility.PRIVATE,
        expires_at=now + timedelta(hours=1),
        created_at=now,
    )
    db_session.add_all([generic_file, try_on_file, linked_diag_file])
    await db_session.commit()
    await db_session.refresh(generic_file)
    await db_session.refresh(try_on_file)
    await db_session.refresh(linked_diag_file)

    db_session.add(
        TryOn(
            user_id=user.id,
            guest_session_id=None,
            job_id=try_on_job.id,
            scope=TryOnScope.PRODUCT_ONLY,
            product_id=product.id,
            saved_coordi_id=None,
            result_file_id=try_on_file.id,
            provider=TryOnProviderKind.MOCK,
            request_json=None,
            saved_at=None,
            expires_at=now - timedelta(minutes=1),
            created_at=now - timedelta(days=1),
        )
    )
    diagnosis = Diagnosis(
        user_id=user.id,
        registered_product_id=registration.id,
        job_id=linked_diagnosis_job.id,
        source_file_id=linked_diag_file.id,
        provider=DiagnosisProviderKind.MOCK,
        repair_needed=True,
        overall_condition="repairRecommended",
        summary="linked diagnosis",
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
    )
    db_session.add(diagnosis)
    await db_session.commit()

    report = await CleanupService(session=db_session, storage=storage).run_once()

    assert report == {
        "expiredTryOns": 1,
        "expiredFiles": 1,
        "expiredJobs": 2,
        "expiredGuestSessions": 1,
    }
    assert await db_session.get(Job, orphan_job.id) is None
    assert await db_session.get(Job, try_on_job.id) is None
    assert await db_session.get(Job, linked_diagnosis_job.id) is not None
    assert await db_session.get(GuestSession, guest.id) is None
    assert await db_session.get(FileMetadata, generic_file.id) is None
    assert await db_session.get(FileMetadata, try_on_file.id) is None
    assert await db_session.get(FileMetadata, linked_diag_file.id) is not None
    assert not storage.resolve_path(generic_file_path).exists()
    assert not storage.resolve_path(try_on_file_path).exists()
    assert storage.resolve_path(linked_diag_file_path).exists()
