from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.files.models import FileMetadata


class FileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, file_metadata: FileMetadata) -> FileMetadata:
        self.session.add(file_metadata)
        await self.session.flush()
        await self.session.refresh(file_metadata)
        return file_metadata

    async def get_by_id(self, file_id: UUID) -> FileMetadata | None:
        result = await self.session.execute(select(FileMetadata).where(FileMetadata.id == file_id))
        return result.scalar_one_or_none()
