from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "CinemaSeat"
    database_url: str = "postgresql+asyncpg://cinemaseat:cinemaseat@db:5432/cinemaseat"
    redis_url: str = "redis://redis:6379/0"
    hold_ttl_seconds: int = Field(gt=0)
    gateway_url: str = "http://gateway:9000"
    gateway_callback_url: str = "http://api:8000/api/v1/payments/callback"
    gateway_otp_callback_url: str = "http://api:8000/api/v1/otp/callback"
    gateway_secret: str = "z2p-2026-secret"
    gateway_request_timeout_seconds: float = Field(default=3, gt=0)
    gateway_max_attempts: int = Field(default=3, ge=1, le=10)


@lru_cache
def get_settings() -> Settings:
    return Settings()
