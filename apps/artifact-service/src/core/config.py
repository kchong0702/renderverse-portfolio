from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, override

from dotenv import load_dotenv
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

_APP_NAME = "artifact-service"

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
    """Application name"""

    env: Env = "dev"
    """Execution environment

    dev: Local device development environment
    staging: Environment for integration and testing
    prod: Production environment
    """

    version: str = "0.1.0"
    """Application's version"""

    cors_origin: list[str] = ["*"]
    """Origins allowed to call the API"""

    route_prefix: str = "/artifact-service"
    """FastAPI router prefix, matching the `tailscale serve` path"""

    host: str = "127.0.0.1"
    """Host address to bind the server to"""

    port: int = 8210
    """Port to listen on"""

    workers: int = 1
    """Number of uvicorn worker processes"""

    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    """Uvicorn log level"""

    access_log: bool = True
    """Enable uvicorn access log"""

    @field_validator("cors_origin", mode="before")
    @classmethod
    def _cors_processor(cls, v: object) -> object:
        return _split_csv(v)


class ObservabilitySettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    service_name: str = _APP_NAME
    """Application service name"""

    log_level: LogLevel = "INFO"
    """Application log level"""

    log_format: LogFormat = "json"
    """Logging format"""

    tracing_enabled: bool = False
    """Whether to export traces over OTLP

    If enabled, otlp_endpoint must be supplied
    """

    metrics_enabled: bool = False
    """Whether to export metrics over OTLP

    If enabled, otlp_endpoint must be supplied
    """

    metrics_export_interval_ms: int = Field(default=60_000, gt=0)
    """Interval between metric exports in milliseconds"""

    otlp_endpoint: HttpUrl | None = None
    """OTLP HTTP base endpoint shared by traces and metrics,
    e.g. http://localhost:4318"""

    otlp_headers: SecretStr | None = None
    """OTLP headers as comma separated key=value pairs,
    ignored when neither tracing nor metrics is enabled"""

    @model_validator(mode="after")
    def _exporters_require_endpoint(self) -> ObservabilitySettings:
        for signal, enabled in (
            ("tracing", self.tracing_enabled),
            ("metrics", self.metrics_enabled),
        ):
            if enabled and self.otlp_endpoint is None:
                raise ValueError(
                    f"observability.{signal}_enabled is True but otlp_endpoint is not set"
                )
        return self


class RendererSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    dist: Path = _ROOT_PATH.parents[1] / "packages/document-renderer/dist/print"
    """The print page that document-renderer builds"""

    templates: Path = _ROOT_PATH.parents[1] / "packages/document-renderer/templates"
    """Folder of the renderer's <id>.yaml template specs"""

    origin: str = "http://renderer/"
    """Made-up origin Chromium loads the print page and assets from, never the network"""

    max_concurrent_renders: int = Field(default=4, gt=0)
    """Renders that may run in Chromium at once, the rest wait their turn"""

    timeout_s: float = Field(default=30, gt=0)
    """Longest one render may take"""


class LibreOfficeSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    command: str = "soffice"
    """LibreOffice command that converts Word files to PDF"""

    max_concurrent_conversions: int = Field(default=2, gt=0)
    """Conversions that may run at once, the rest wait their turn"""

    timeout_s: float = Field(default=60, gt=0)
    """Longest one conversion may take"""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ARTIFACT_SERVICE_",
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
    """Application and uvicorn server settings"""

    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    """Logging, tracing and metrics settings"""

    renderer: RendererSettings = Field(default_factory=RendererSettings)
    """Headless Chromium and the document renderer it loads"""

    libreoffice: LibreOfficeSettings = Field(default_factory=LibreOfficeSettings)
    """LibreOffice, which converts Word files to PDF"""

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
    "LibreOfficeSettings",
    "ObservabilitySettings",
    "RendererSettings",
    "Settings",
    "get_settings",
    "reload_settings",
]
