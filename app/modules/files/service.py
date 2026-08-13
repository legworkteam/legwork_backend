from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.ownership import Principal, ensure_file_access
from app.core.enums import FileOwnerType, FileVisibility, PrincipalType
from app.core.exceptions import NotFoundError
from app.modules.files.models import FileMetadata
from app.modules.files.repository import FileRepository
from app.modules.files.schemas import FileMetadataSchema
from app.storage.base import StorageService
from app.storage.local import LocalStorageService
from app.storage.paths import build_private_upload_path
from app.utils.ids import new_uuid


@dataclass(frozen=True)
class StoredPrivateFile:
    metadata: FileMetadata
    content: bytes


class FileService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        repository: FileRepository | None = None,
        storage: StorageService | None = None,
    ) -> None:
        self.session = session
        self.repository = repository or FileRepository(session)
        self.storage = storage or LocalStorageService()

    async def create_private_file(
        self,
        *,
        owner_type: FileOwnerType,
        owner_id: UUID,
        filename: str,
        content_type: str,
        content: bytes,
        expires_at: datetime | None = None,
    ) -> FileMetadataSchema:
        file_id = new_uuid()
        relative_path = build_private_upload_path(
            owner_type=owner_type,
            owner_id=owner_id,
            file_id=file_id,
            filename=filename,
        )
        write_result = await self.storage.save(relative_path=relative_path, content=content)
        metadata = FileMetadata(
            id=file_id,
            owner_type=owner_type,
            owner_id=owner_id,
            path=write_result.relative_path,
            original_name=filename,
            content_type=content_type,
            size=write_result.size,
            visibility=FileVisibility.PRIVATE,
            expires_at=expires_at,
        )
        try:
            await self.repository.add(metadata)
            await self.session.commit()
        except Exception:
            await self.storage.delete(relative_path=write_result.relative_path)
            raise
        return FileMetadataSchema.model_validate(metadata)

    async def get_owned_file(self, *, file_id: UUID, principal: Principal) -> StoredPrivateFile:
        metadata = await self.repository.get_by_id(file_id)
        if metadata is None:
            raise NotFoundError("File not found.")

        ensure_file_access(
            principal,
            owner_type=metadata.owner_type.value,
            owner_id=metadata.owner_id,
        )
        content = await self.storage.open(relative_path=metadata.path)
        return StoredPrivateFile(metadata=metadata, content=content)

    @staticmethod
    def owner_type_for_principal(principal: Principal) -> FileOwnerType:
        if principal.type is PrincipalType.USER:
            return FileOwnerType.USER
        return FileOwnerType.GUEST
