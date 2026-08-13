from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import FileOwnerType, FileVisibility


class FileMetadataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    owner_type: FileOwnerType = Field(alias="ownerType")
    owner_id: UUID | None = Field(alias="ownerId")
    original_name: str = Field(alias="originalName")
    content_type: str = Field(alias="contentType")
    size: int
    visibility: FileVisibility
    expires_at: datetime | None = Field(alias="expiresAt")
    created_at: datetime = Field(alias="createdAt")
