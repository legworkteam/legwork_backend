from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: str = Field(default="local", alias="APP_ENV")
    app_name: str = Field(default="Atelier Lens API", alias="APP_NAME")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    database_url: str = Field(
        default="postgresql+asyncpg://atelier_lens:atelier_lens@localhost:5432/atelier_lens",
        alias="DATABASE_URL",
    )

    jwt_secret_key: str = Field(default="change-me", alias="JWT_SECRET_KEY")
    access_token_expire_minutes: int = Field(default=120, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=14, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    file_root: str = Field(default="./data", alias="FILE_ROOT")
    ai_http_timeout_seconds: int = Field(default=60, alias="AI_HTTP_TIMEOUT_SECONDS")
    guest_photo_limit: int = Field(default=3, alias="GUEST_PHOTO_LIMIT")
    tryon_source_ttl_minutes: int = Field(default=60, alias="TRYON_SOURCE_TTL_MINUTES")
    tryon_result_ttl_minutes: int = Field(default=180, alias="TRYON_RESULT_TTL_MINUTES")
    job_ttl_hours: int = Field(default=24, alias="JOB_TTL_HOURS")

    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    kakao_client_id: str = Field(default="", alias="KAKAO_CLIENT_ID")
    kakao_client_secret: str = Field(default="", alias="KAKAO_CLIENT_SECRET")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
