"""
Central application configuration.

Every value that differs between local/staging/production lives here and is
sourced from environment variables (.env locally, real secrets in deploy).
Nothing in this file is a stand-in value used at runtime - SECRET_KEY and
DATABASE_URL have no defaults on purpose, so the app refuses to boot with
unsafe placeholders.
"""
from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # --- Core ---
    APP_NAME: str = "AcneTrex"
    APP_VERSION: str = "3.0.0"
    SCHEMA_VERSION: int = 3
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    # --- Auth / security ---
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REMEMBER_ME_EXPIRE_DAYS: int = 90
    RESET_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"

    # --- Database ---
    DATABASE_URL: PostgresDsn
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # --- Redis / background jobs ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- Object storage (consented images) ---
    S3_ENDPOINT_URL: str | None = None
    S3_BUCKET: str = "acnetrex-scans"
    S3_REGION: str = "auto"
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None

    # --- AI / model providers ---
    ANTHROPIC_API_KEY: str | None = None
    ASSISTANT_MODEL: str = "claude-sonnet-4-6"
    EMBEDDING_DIM: int = 1536

    # --- CORS ---
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    # --- ML acceptance thresholds (used by validation_service) ---
    MIN_FACE_CONFIDENCE: float = 0.72
    MIN_IMAGE_QUALITY_SCORE: float = 0.55
    FORECAST_MIN_DAYS_REQUIRED: int = 7

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_strong(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters. Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\"")
        return v

    @property
    def db_url_str(self) -> str:
        return str(self.DATABASE_URL)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
