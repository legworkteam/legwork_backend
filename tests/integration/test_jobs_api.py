from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.ownership import Principal
from app.core.enums import JobStatus, JobType, PrincipalType
from app.modules.jobs.service import JobService


@pytest.mark.asyncio
async def test_job_owner_can_read_job(db_session, client: TestClient) -> None:
    owner_id = uuid4()
    service = JobService(db_session)
    created = await service.create_job(
        principal=Principal(type=PrincipalType.USER, owner_id=owner_id),
        job_type=JobType.AVATAR_TRY_ON,
    )

    response = client.get(
        f"/api/v1/jobs/{created.id}",
        headers={"Authorization": f"Bearer user:{owner_id}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["jobId"] == str(created.id)
    assert body["data"]["status"] == JobStatus.PENDING.value
    assert body["data"]["type"] == JobType.AVATAR_TRY_ON.value


@pytest.mark.asyncio
async def test_job_rejects_other_owner(db_session, client: TestClient) -> None:
    owner_id = uuid4()
    other_owner_id = uuid4()
    service = JobService(db_session)
    created = await service.create_job(
        principal=Principal(type=PrincipalType.GUEST, owner_id=owner_id),
        job_type=JobType.PHOTO_TRY_ON,
    )

    response = client.get(
        f"/api/v1/jobs/{created.id}",
        headers={"Authorization": f"Bearer guest:{other_owner_id}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_jobs_and_files_are_exposed_in_openapi(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/jobs/{jobId}" in paths
    assert "/api/v1/files/{fileId}" in paths
