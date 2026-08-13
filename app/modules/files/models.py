from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.enums import FileOwnerType, FileVisibility
from app.utils.datetime import now_kst
from app.utils.ids import new_uuid


def _enum_values(enum_cls: type[FileOwnerType] | type[FileVisibility]) -> list[str]:
    return [member.value for member in enum_cls]


class FileMetadata(Base):
    __tablename__ = "fileMetadata"
    __table_args__ = (
        Index("ix_fileMetadata_ownerType_ownerId", "ownerType", "ownerId"),
        Index("ix_fileMetadata_expiresAt", "expiresAt"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=new_uuid)
    owner_type: Mapped[FileOwnerType] = mapped_column(
        "ownerType",
        Enum(FileOwnerType, name="file_owner_type", values_callable=_enum_values),
    )
    owner_id: Mapped[UUID | None] = mapped_column("ownerId", nullable=True)
    path: Mapped[str] = mapped_column(Text)
    original_name: Mapped[str] = mapped_column("originalName", String(255))
    content_type: Mapped[str] = mapped_column("contentType", String(100))
    size: Mapped[int] = mapped_column(BigInteger)
    visibility: Mapped[FileVisibility] = mapped_column(
        Enum(FileVisibility, name="file_visibility", values_callable=_enum_values),
        default=FileVisibility.PRIVATE,
    )
    expires_at: Mapped[datetime | None] = mapped_column("expiresAt", DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "createdAt",
        DateTime(timezone=True),
        default=now_kst,
    )
