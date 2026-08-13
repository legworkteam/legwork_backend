from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.enums import FileOwnerType
from app.modules.files.service import FileService


@pytest.mark.asyncio
async def test_private_file_owner_can_download(db_session, client: TestClient) -> None:
    owner_id = uuid4()
    service = FileService(db_session)
    created = await service.create_private_file(
        owner_type=FileOwnerType.USER,
        owner_id=owner_id,
        filename="private.jpg",
        content_type="image/jpeg",
        content=b"\xff\xd8\xff\xe0private",
    )

    response = client.get(
        f"/api/v1/files/{created.id}",
        headers={"Authorization": f"Bearer user:{owner_id}"},
    )

    assert response.status_code == 200
    assert response.content == b"\xff\xd8\xff\xe0private"
    assert response.headers["content-type"].startswith("image/jpeg")
    assert "uploads/" not in response.text


@pytest.mark.asyncio
async def test_private_file_rejects_other_owner(db_session, client: TestClient) -> None:
    owner_id = uuid4()
    other_owner_id = uuid4()
    service = FileService(db_session)
    created = await service.create_private_file(
        owner_type=FileOwnerType.GUEST,
        owner_id=owner_id,
        filename="guest.png",
        content_type="image/png",
        content=b"\x89PNG\r\n\x1a\nguest",
    )

    response = client.get(
        f"/api/v1/files/{created.id}",
        headers={"Authorization": f"Bearer guest:{other_owner_id}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
