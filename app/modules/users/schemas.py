"""Member account schemas (camelCase JSON)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import AuthProvider
from app.core.security import password_meets_policy


class MeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID = Field(alias="userId")
    name: str
    email: str | None = None
    phone: str | None = None
    auth_provider: AuthProvider = Field(alias="authProvider")
    has_avatar: bool = Field(alias="hasAvatar")
    created_at: datetime = Field(alias="createdAt")


class UpdateMeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=80)
    phone: str | None = Field(default=None, max_length=30)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    current_password: str = Field(alias="currentPassword")
    new_password: str = Field(alias="newPassword")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value: str) -> str:
        if not password_meets_policy(value):
            raise ValueError(
                "비밀번호는 8자 이상이며 대문자/숫자/특수문자를 포함해야 합니다."
            )
        return value
