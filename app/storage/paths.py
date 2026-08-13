from pathlib import Path
from uuid import UUID

from app.core.enums import FileOwnerType
from app.utils.ids import new_uuid


def build_private_upload_path(*, owner_type: FileOwnerType, owner_id: UUID, file_id: UUID, filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if owner_type is FileOwnerType.GUEST:
        prefix = Path("uploads") / "guests" / str(owner_id)
    elif owner_type is FileOwnerType.USER:
        prefix = Path("uploads") / "members" / str(owner_id)
    elif owner_type is FileOwnerType.PRODUCT:
        prefix = Path("products") / str(owner_id)
    else:
        prefix = Path("temporary")
    return (prefix / f"{file_id}{suffix}").as_posix()


def build_temporary_path(*, purpose: str, filename: str) -> str:
    suffix = Path(filename).suffix.lower() or ".bin"
    return (Path("temporary") / purpose / f"{new_uuid()}{suffix}").as_posix()
