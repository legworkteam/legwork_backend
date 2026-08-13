from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import Principal
from app.core.enums import AuthProvider, JobStatus, JobType
from app.core.security import create_access_token, create_guest_token
from app.modules.guests.models import GuestSession
from app.modules.jobs.service import JobService
from app.modules.users.models import User
from app.utils.datetime import now_kst


async def _create_user(db_session) -> User:
    user = User(
        name="Job Owner",
        email=f"job-{uuid4().hex}@example.com",
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
async def test_job_owner_can_read_job(db_session, client: TestClient) -> None:
    user = await _create_user(db_session)
    service = JobService(db_session)
    created = await service.create_job(
        principal=Principal(kind="member", user_id=user.id),
        job_type=JobType.AVATAR_TRY_ON,
    )

    response = client.get(
        f"/api/v1/jobs/{created.id}",
        headers={"Authorization": f"Bearer {create_access_token(str(user.id))}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["jobId"] == str(created.id)
    assert body["data"]["status"] == JobStatus.PENDING.value
    assert body["data"]["type"] == JobType.AVATAR_TRY_ON.value


@pytest.mark.asyncio
async def test_job_rejects_other_owner(db_session, client: TestClient) -> None:
    owner = await _create_guest_session(db_session)
    other_owner = await _create_guest_session(db_session)
    service = JobService(db_session)
    created = await service.create_job(
        principal=Principal(kind="guest", guest_session_id=owner.id),
        job_type=JobType.PHOTO_TRY_ON,
    )

    response = client.get(
        f"/api/v1/jobs/{created.id}",
        headers={"Authorization": f"Bearer {create_guest_token(str(other_owner.id), other_owner.expires_at)}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_jobs_and_files_are_exposed_in_openapi(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/jobs/{jobId}" in paths
    assert "/api/v1/files/{fileId}" in paths
