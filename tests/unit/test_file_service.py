from uuid import uuid4

import pytest

from app.api.dependencies.ownership import Principal
from app.core.enums import FileOwnerType, PrincipalType
from app.modules.files.service import FileService


@pytest.mark.asyncio
async def test_file_metadata_is_created_and_saved(db_session) -> None:
    owner_id = uuid4()
    service = FileService(db_session)

    created = await service.create_private_file(
        owner_type=FileOwnerType.USER,
        owner_id=owner_id,
        filename="profile.jpg",
        content_type="image/jpeg",
        content=b"\xff\xd8\xff\xe0test",
    )

    assert created.owner_type == FileOwnerType.USER
    assert created.owner_id == owner_id
    assert created.original_name == "profile.jpg"
    assert created.content_type == "image/jpeg"
    assert created.size == len(b"\xff\xd8\xff\xe0test")


@pytest.mark.asyncio
async def test_private_file_owner_can_read_saved_content(db_session) -> None:
    owner_id = uuid4()
    service = FileService(db_session)
    created = await service.create_private_file(
        owner_type=FileOwnerType.GUEST,
        owner_id=owner_id,
        filename="guest.png",
        content_type="image/png",
        content=b"\x89PNG\r\n\x1a\ncontent",
    )

    stored = await service.get_owned_file(
        file_id=created.id,
        principal=Principal(type=PrincipalType.GUEST, owner_id=owner_id),
    )

    assert stored.content == b"\x89PNG\r\n\x1a\ncontent"
    assert stored.metadata.path.startswith("uploads/guests/")
