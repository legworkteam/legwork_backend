from datetime import timedelta
from io import BytesIO
from uuid import uuid4

import pytest
from fastapi import BackgroundTasks
from starlette.datastructures import UploadFile

from app.api.dependencies.auth import Principal
from app.core.enums import AuthProvider, Gender, TryOnScope
from app.core.exceptions import GuestLimitExceededError
from app.modules.products.models import Product
from app.modules.products.repository import ProductRepository
from app.modules.products.service import ProductService
from app.modules.try_on.repository import TryOnRepository
from app.modules.try_on.schemas import AvatarTryOnRequest, PhotoTryOnRequest
from app.modules.try_on.service import TryOnService
from app.modules.users.models import User
from app.modules.guests.models import GuestSession
from app.providers.try_on.base import TryOnProviderRequest, TryOnProviderResult
from app.storage.local import LocalStorageService
from app.utils.datetime import now_kst


class StubProvider:
    def __init__(self) -> None:
        self.calls: list[TryOnProviderRequest] = []

    async def generate(self, payload: TryOnProviderRequest) -> TryOnProviderResult:
        self.calls.append(payload)
        return TryOnProviderResult(
            filename="result.png",
            content_type="image/png",
            content=b"\x89PNG\r\n\x1a\nok",
            provider="mock",
        )


@pytest.mark.asyncio
async def test_try_on_service_enqueues_avatar_job(db_session) -> None:
    user = User(
        name="TryOnSvc",
        email=f"tryon-svc-{uuid4().hex}@example.com",
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
        name="Demo",
        description=None,
        category="bag",
        base_price=1000,
        currency="KRW",
        active=True,
    )
    db_session.add_all([user, product])
    await db_session.commit()
    await db_session.refresh(user)
    await db_session.refresh(product)

    service = TryOnService(
        db_session,
        product_service=ProductService(ProductRepository(db_session)),
        provider=StubProvider(),
        storage=LocalStorageService(),
        try_on_repository=TryOnRepository(db_session),
    )

    accepted = await service.enqueue_avatar_try_on(
        principal=Principal(kind="member", user_id=user.id),
        payload=AvatarTryOnRequest(scope=TryOnScope.PRODUCT_ONLY, productId=product.id),
        background_tasks=BackgroundTasks(),
    )

    assert accepted.job_id is not None


@pytest.mark.asyncio
async def test_try_on_service_enforces_guest_limit(db_session) -> None:
    guest = GuestSession(
        expires_at=now_kst() + timedelta(hours=2),
        qr_code_id=None,
        height_cm=None,
        weight_kg=None,
        gender=Gender.NEUTRAL,
        photo_try_on_count=3,
    )
    product = Product(
        product_code="DEMO-BAG-002",
        name="Demo2",
        description=None,
        category="bag",
        base_price=1000,
        currency="KRW",
        active=True,
    )
    db_session.add_all([guest, product])
    await db_session.commit()
    await db_session.refresh(guest)
    await db_session.refresh(product)

    service = TryOnService(
        db_session,
        product_service=ProductService(ProductRepository(db_session)),
        provider=StubProvider(),
        storage=LocalStorageService(),
        try_on_repository=TryOnRepository(db_session),
    )

    with pytest.raises(GuestLimitExceededError):
        await service.enqueue_photo_try_on(
            principal=Principal(kind="guest", guest_session_id=guest.id),
            payload=PhotoTryOnRequest(scope=TryOnScope.PRODUCT_ONLY, productId=product.id),
            photo=UploadFile(filename="person.jpg", file=BytesIO(b"\xff\xd8\xff\xe0content")),
            background_tasks=BackgroundTasks(),
        )
