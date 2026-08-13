from uuid import uuid4

import pytest

from app.api.dependencies.ownership import Principal
from app.core.enums import JobStatus, JobType, PrincipalType
from app.modules.jobs.service import JobService


@pytest.mark.asyncio
async def test_job_creation_sets_owner_and_expiry(db_session) -> None:
    owner_id = uuid4()
    service = JobService(db_session)

    created = await service.create_job(
        principal=Principal(type=PrincipalType.USER, owner_id=owner_id),
        job_type=JobType.PHOTO_TRY_ON,
    )

    assert created.type == JobType.PHOTO_TRY_ON
    assert created.status == JobStatus.PENDING
    assert created.progress == 0
    assert created.expires_at > created.created_at


@pytest.mark.asyncio
async def test_job_status_transition_updates_result(db_session) -> None:
    owner_id = uuid4()
    service = JobService(db_session)
    created = await service.create_job(
        principal=Principal(type=PrincipalType.GUEST, owner_id=owner_id),
        job_type=JobType.DIAGNOSIS,
    )

    updated = await service.update_status(
        job_id=created.id,
        status=JobStatus.SUCCEEDED,
        progress=100,
        result_json={"resultFileId": str(uuid4())},
    )

    assert updated.status == JobStatus.SUCCEEDED
    assert updated.progress == 100
    assert updated.result_json is not None
    assert "resultFileId" in updated.result_json
