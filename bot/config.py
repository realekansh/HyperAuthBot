from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    BOT_TOKEN: str = Field(..., min_length=10)
    OWNER_ID: int
    MINI_APP_URL: str
    WEBHOOK_URL: str = ""
    WEBHOOK_SECRET: str = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///./hyperauth_guardian.db"
    PORT: int = 8000
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    @field_validator("MINI_APP_URL")
    @classmethod
    def mini_app_url_must_be_https_or_local(cls, value: str) -> str:
        if not (value.startswith("https://") or value.startswith("http://localhost") or value.startswith("http://127.0.0.1")):
            raise ValueError("MINI_APP_URL must be HTTPS in production")
        return value.rstrip("/")

    @field_validator("WEBHOOK_URL")
    @classmethod
    def webhook_url_must_be_https_or_empty(cls, value: str) -> str:
        if value and not value.startswith("https://"):
            raise ValueError("WEBHOOK_URL must be HTTPS when set")
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
