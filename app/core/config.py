from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Real Estate Property Consultant GIS Service"
    app_version: str = "0.1.0"
    environment: Literal["local", "test", "production"] = "local"
    debug: bool = True
    log_level: str = "DEBUG"
    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(
        default="postgresql+psycopg://postgres:password@host.docker.internal:5432/realestate_db",
        min_length=1,
        description="SQLAlchemy database URL for local PostgreSQL with PostGIS.",
    )
    sql_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout_seconds: int = 30

    default_search_page_size: int = 20
    max_search_page_size: int = 100
    default_nearby_radius_m: int = 3000
    max_nearby_radius_m: int = 25000

    n8n_webhook_base_url: str | None = None
    gemini_api_key: str | None = None

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no", "off"}:
                return False
            if normalized in {"debug", "dev", "local", "true", "1", "yes", "on"}:
                return True
        return value

    @field_validator("log_level", mode="before")
    @classmethod
    def parse_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().upper()
            if normalized in {"DEBUG", "DEBU"}:
                return "DEBUG"
            if normalized in {"INFO", "INF"}:
                return "INFO"
            if normalized in {"WARNING", "WARN", "WRN"}:
                return "WARNING"
            if normalized in {"ERROR", "ERR"}:
                return "ERROR"
            if normalized in {"CRITICAL", "FATAL"}:
                return "CRITICAL"
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
