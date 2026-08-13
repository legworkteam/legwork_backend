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


class AuthProvider(StrEnum):
    LOCAL = "local"
    GOOGLE = "google"
    KAKAO = "kakao"


class Gender(StrEnum):
    FEMALE = "female"
    MALE = "male"
    NEUTRAL = "neutral"
