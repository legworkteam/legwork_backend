"""Auth request/response schemas (camelCase JSON)."""

import re
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.security import password_meets_policy

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str
    password: str
    name: str = Field(min_length=1, max_length=80)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL_RE.match(value):
            raise ValueError("이메일 형식이 올바르지 않습니다.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not password_meets_policy(value):
            raise ValueError(
                "비밀번호는 8자 이상이며 대문자/숫자/특수문자를 포함해야 합니다."
            )
        return value


class SignupResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID = Field(alias="userId")


class LoginRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    email: str
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.strip().lower()


class TokenResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_id: uuid.UUID = Field(alias="userId")
    access_token: str = Field(alias="accessToken")
    refresh_token: str = Field(alias="refreshToken")
    access_token_expires_in: int = Field(alias="accessTokenExpiresIn")
    refresh_token_expires_in: int = Field(alias="refreshTokenExpiresIn")


class SocialLoginRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    provider: str
    authorization_code: str = Field(alias="authorizationCode", min_length=1)
    redirect_uri: str | None = Field(default=None, alias="redirectUri")

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"google", "kakao"}:
            raise ValueError("provider는 google 또는 kakao여야 합니다.")
        return value


class RefreshRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(alias="refreshToken")


class LogoutRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    refresh_token: str = Field(alias="refreshToken")


class ClaimRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    guest_token: str = Field(alias="guestToken")


class ClaimResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    recent_products_claimed: int = Field(alias="recentProductsClaimed")
