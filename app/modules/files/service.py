from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import Principal
from app.core.enums import FileOwnerType, FileVisibility
from app.core.exceptions import ForbiddenError, NotFoundError
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
        return await self._create_file(
            owner_type=owner_type,
            owner_id=owner_id,
            filename=filename,
            content_type=content_type,
            content=content,
            visibility=FileVisibility.PRIVATE,
            expires_at=expires_at,
        )

    async def create_public_file(
        self,
        *,
        owner_type: FileOwnerType,
        owner_id: UUID,
        filename: str,
        content_type: str,
        content: bytes,
    ) -> FileMetadataSchema:
        """Public file (e.g. product images): fetchable by any principal, no
        owner-match check, never TTL-expired."""
        return await self._create_file(
            owner_type=owner_type,
            owner_id=owner_id,
            filename=filename,
            content_type=content_type,
            content=content,
            visibility=FileVisibility.PUBLIC,
            expires_at=None,
        )

    async def _create_file(
        self,
        *,
        owner_type: FileOwnerType,
        owner_id: UUID,
        filename: str,
        content_type: str,
        content: bytes,
        visibility: FileVisibility,
        expires_at: datetime | None,
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
            visibility=visibility,
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

        # Public files (e.g. product images) are fetchable by any principal;
        # visibility governs access here, not ownership.
        if metadata.visibility is FileVisibility.PUBLIC:
            content = await self.storage.open(relative_path=metadata.path)
            return StoredPrivateFile(metadata=metadata, content=content)

        if metadata.owner_id is None:
            raise ForbiddenError("Owner is not assigned to this file.")

        if principal.kind == "member":
            if metadata.owner_type is not FileOwnerType.USER or metadata.owner_id != principal.user_id:
                raise ForbiddenError("You do not own this file.")
        else:
            if metadata.owner_type is not FileOwnerType.GUEST or metadata.owner_id != principal.guest_session_id:
                raise ForbiddenError("You do not own this file.")

        content = await self.storage.open(relative_path=metadata.path)
        return StoredPrivateFile(metadata=metadata, content=content)

    @staticmethod
    def owner_type_for_principal(principal: Principal) -> FileOwnerType:
        return FileOwnerType.USER if principal.kind == "member" else FileOwnerType.GUEST
