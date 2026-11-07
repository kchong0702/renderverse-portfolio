from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, override

from dotenv import load_dotenv
from pydantic import (
    AliasChoices,
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

_APP_NAME = "ezcareer-harness"

_ROOT_PATH = Path(__file__).resolve().parents[2]
_DEFAULT_TOML = _ROOT_PATH / "config.toml"
_DEFAULT_ENV_FILE = _ROOT_PATH / ".env"

load_dotenv(_DEFAULT_ENV_FILE, override=False)

Env = Literal["dev", "staging", "prod"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["json", "console"]

Instrumentation = Literal["langchain"]


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

    route_prefix: str = "/ezcareer"
    """FastAPI router prefix, matching the `tailscale serve` path"""

    host: str = "127.0.0.1"
    """Host address to bind the server to"""

    port: int = 8200
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


class TraceRedactionSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    hide_inputs: bool = False
    """Hide everything a span received: the input value (replaced with
    "__REDACTED__"), LLM input messages, prompts, tool definitions and input
    images"""

    hide_outputs: bool = False
    """Hide everything a span produced: the output value (replaced with
    "__REDACTED__"), LLM output messages, choices and output images"""

    hide_input_messages: bool = False
    """Drop LLM input messages from spans, keeping the span's input value"""

    hide_output_messages: bool = False
    """Drop LLM output messages from spans, keeping the span's output value"""

    hide_input_text: bool = False
    """Redact only the text of LLM input messages, keeping roles and message
    structure"""

    hide_output_text: bool = False
    """Redact only the text of LLM output messages, keeping roles and message
    structure"""

    hide_input_images: bool = False
    """Drop images from LLM input messages"""

    hide_embedding_vectors: bool = False
    """Redact embedding vectors"""

    hide_embeddings_text: bool = False
    """Redact the text that was embedded"""

    hide_llm_invocation_parameters: bool = False
    """Drop LLM invocation parameters, e.g. model name, temperature and max
    tokens"""

    base64_image_max_length: int = 32_000
    """Maximum length of a base64 image data URI kept on a span; longer
    images are redacted"""


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
    """OpenInference instrumentations to enable when tracing is on"""

    trace_redaction: TraceRedactionSettings = TraceRedactionSettings()
    """What instrumented spans hide or redact"""

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


class AgentSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    name: str
    """Agent name, such as career-consultant"""

    path: Path
    """The agent's profile.yaml, relative to the app folder; its folder holds
    system.md and skills/"""

    model: str
    """Exact model the agent runs on, such as glm-5.3; profile.yaml must hold
    its harness profile"""

    @field_validator("path")
    @classmethod
    def _from_app_folder(cls, path: Path) -> Path:
        """Reads a relative path from the app folder"""
        return path if path.is_absolute() else _ROOT_PATH / path


class FlowSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    name: str
    """Flow name, such as edit"""

    path: Path
    """The flow's yaml of graph settings, such as its checks and recursion
    limit, relative to the app folder"""

    @field_validator("path")
    @classmethod
    def _from_app_folder(cls, path: Path) -> Path:
        """Reads a relative path from the app folder"""
        return path if path.is_absolute() else _ROOT_PATH / path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EZCAREER_HARNESS_",
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

    agents: tuple[AgentSettings, ...] = ()
    """Every agent the app builds, read from config.toml's [[agents]] tables"""

    flows: list[FlowSettings] = Field(default_factory=list)
    """Every flow's graph settings file, read from config.toml's [[flows]] tables"""

    gateway_url: HttpUrl | None = Field(
        default=None, validation_alias=AliasChoices("AIGW_UPSTREAM_URL", "gateway_url")
    )
    """OpenAI-compatible gateway that serves the glm and openai model families"""

    gateway_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("AIGW_PASSTHROUGH_KEY", "gateway_key"),
    )
    """Key for the model gateway"""

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
            TomlConfigSettingsSource(
                settings_cls,
                toml_file=os.environ.get("EZCAREER_HARNESS_CONFIG", _DEFAULT_TOML),
            ),
            file_secret_settings,
        )

    def flow(self, name: str) -> Path:
        """The graph settings file of the flow with that name"""
        [flow] = [flow for flow in self.flows if flow.name == name]
        return flow.path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get settings instance, singleton per process"""
    return Settings()


def reload_settings() -> Settings:
    """Reset settings instance"""
    get_settings.cache_clear()
    return get_settings()


__all__ = [
    "AgentSettings",
    "AppSettings",
    "FlowSettings",
    "Instrumentation",
    "ObservabilitySettings",
    "Settings",
    "TraceRedactionSettings",
    "get_settings",
    "reload_settings",
]
