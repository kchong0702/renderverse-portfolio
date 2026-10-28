from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, override

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

_APP_NAME = "folio"

_ROOT_PATH = Path(__file__).resolve().parents[2]
_DEFAULT_TOML = _ROOT_PATH / "config.toml"
_DEFAULT_ENV_FILE = _ROOT_PATH / ".env"

load_dotenv(_DEFAULT_ENV_FILE, override=False)

Env = Literal["dev", "staging", "prod"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["json", "console"]


def _split_csv(v: object) -> object:
    if isinstance(v, str):
        return [item.strip() for item in v.split(",") if item.strip()]
    return v


class AppSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    name: str = _APP_NAME
    env: Env = "dev"
    version: str = "0.1.0"
    cors_origin: list[str] = ["*"]
    route_prefix: str = "/folio"
    """FastAPI router prefix, matching the `tailscale serve` path"""

    host: str = "127.0.0.1"
    port: int = 8200
    workers: int = 1
    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    access_log: bool = True

    @field_validator("cors_origin", mode="before")
    @classmethod
    def _cors_processor(cls, v: object) -> object:
        return _split_csv(v)


class ObservabilitySettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    service_name: str = _APP_NAME
    log_level: LogLevel = "INFO"
    log_format: LogFormat = "json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FOLIO_",
        env_nested_delimiter="__",
        env_file=str(_DEFAULT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        frozen=True,
        validate_default=True,
        toml_file=str(_DEFAULT_TOML),
    )

    app: AppSettings = Field(default_factory=AppSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)

    @classmethod
    @override
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            TomlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get settings instance, singleton per process"""
    return Settings()


def reload_settings() -> Settings:
    """Reset settings instance"""
    get_settings.cache_clear()
    return get_settings()


__all__ = [
    "AppSettings",
    "ObservabilitySettings",
    "Settings",
    "get_settings",
    "reload_settings",
]
