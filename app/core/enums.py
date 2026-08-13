from enum import StrEnum


class FileOwnerType(StrEnum):
    GUEST = "guest"
    USER = "user"
    PRODUCT = "product"
    SYSTEM = "system"


class FileVisibility(StrEnum):
    PRIVATE = "private"
    PUBLIC = "public"


class JobType(StrEnum):
    AVATAR_TRY_ON = "avatarTryOn"
    PHOTO_TRY_ON = "photoTryOn"
    DIAGNOSIS = "diagnosis"


class JobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PrincipalType(StrEnum):
    USER = "user"
    GUEST = "guest"
