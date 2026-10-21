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

_APP_NAME = "ezbot"

_ROOT_PATH = Path(__file__).resolve().parents[2]
_DEFAULT_TOML = _ROOT_PATH / "config.toml"
_DEFAULT_ENV_FILE = _ROOT_PATH / ".env"

load_dotenv(_DEFAULT_ENV_FILE, override=False)

Env = Literal["dev", "staging", "prod"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["json", "console"]

Instrumentation = Literal["langchain"]


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
    """Cors origins"""

    route_prefix: str = "/ezbot"
    """FastAPI router prefix"""

    host: str = "127.0.0.1"
    """Host address to bind the server to"""

    port: int = 8000
    """Port to listen on"""

    workers: int = 1
    """Number of uvicorn worker processes (set >1 for production)"""

    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    """Uvicorn log level"""

    access_log: bool = True
    """Enable uvicorn access log"""

    @field_validator("cors_origin", mode="before")
    @classmethod
    def _cors_processor(cls, v):
        if isinstance(v, str):
            return v.split(",")
        return v


class ChatSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    max_message_chars: int = 2000
    """Maximum characters of a user message"""

    max_reply_chars: int = 8000
    """Maximum characters of a bot reply sent back as history"""

    max_history: int = 20
    """Maximum number of prior messages the client may send as context"""


class TraceRedactionSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    hide_inputs: bool = False
    hide_outputs: bool = False
    hide_input_messages: bool = False
    hide_output_messages: bool = False
    hide_input_text: bool = False
    hide_output_text: bool = False
    hide_input_images: bool = False
    hide_embedding_vectors: bool = False
    hide_embeddings_text: bool = False
    hide_llm_invocation_parameters: bool = False
    base64_image_max_length: int = 32_000


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

    instrumentations: tuple[Instrumentation, ...] = ()
    """Open Inference instrument"""

    trace_redaction: TraceRedactionSettings = TraceRedactionSettings()
    """Trace redaction setting for instrument"""

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


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EZBOT_",
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
    chat: ChatSettings = Field(default_factory=ChatSettings)
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
    "ChatSettings",
    "Instrumentation",
    "ObservabilitySettings",
    "Settings",
    "TraceRedactionSettings",
    "get_settings",
    "reload_settings",
]
