"""Shared enums exposed across domains.

Values are the exact strings used in API JSON (camelCase where relevant),
so DB enum values and API responses stay in sync. `core` is owned by
Backend A; extend with agreement per the collaboration rules.
"""

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


def pg_enum(enum_cls: type[StrEnum], name: str) -> SAEnum:
    """SQLAlchemy Enum that persists the member *value* (camelCase), not name."""
    return SAEnum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


# --- Backend A (Core & Commerce) --------------------------------------------
class AuthProvider(StrEnum):
    LOCAL = "local"
    GOOGLE = "google"
    KAKAO = "kakao"


class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"
    NEUTRAL = "neutral"


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    READY = "ready"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class RegisteredProductSource(StrEnum):
    PURCHASE = "purchase"
    MANUAL = "manual"


# --- Backend B (Experience & AI) --------------------------------------------
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
