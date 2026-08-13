from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.enums import Gender
from app.modules.avatars.repository import AvatarRepository
from app.modules.avatars.schemas import AvatarParametersPayload
from app.modules.avatars.service import AvatarAlreadyExistsError, AvatarService
from app.modules.guests.models import GuestSession
from app.modules.guests.repository import GuestRepository
from app.modules.users.models import User
from app.core.enums import AuthProvider
from app.utils.datetime import now_kst


@pytest.mark.asyncio
async def test_avatar_service_create_and_duplicate(db_session) -> None:
    user = User(
        name="AvatarSvc",
        email=f"avatar-svc-{uuid4().hex}@example.com",
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

    service = AvatarService(AvatarRepository(db_session), guest_repository=GuestRepository(db_session))
    payload = AvatarParametersPayload(heightCm=172, weightKg=65, gender=Gender.FEMALE)

    created = await service.create_member_avatar(user_id=user.id, payload=payload)
    assert created.user_id == user.id

    with pytest.raises(AvatarAlreadyExistsError):
        await service.create_member_avatar(user_id=user.id, payload=payload)


@pytest.mark.asyncio
async def test_avatar_service_updates_guest_parameters(db_session) -> None:
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

    service = AvatarService(AvatarRepository(db_session), guest_repository=GuestRepository(db_session))
    updated = await service.update_guest_avatar_parameters(
        guest_session_id=guest.id,
        payload=AvatarParametersPayload(heightCm=168, weightKg=57, gender=Gender.MALE),
    )

    assert updated.gender == Gender.MALE
    await db_session.refresh(guest)
    assert float(guest.height_cm) == 168
