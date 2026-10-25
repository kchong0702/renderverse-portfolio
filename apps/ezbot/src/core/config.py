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

Provider = Literal[
    "groq", "mistralai", "google_genai", "openrouter", "openai_compatible"
]


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

    cors_origin: list[str] = []
    """Origins allowed to call the API"""

    route_prefix: str = "/ezbot"
    """FastAPI router prefix"""

    host: str = "127.0.0.1"
    """Host address to bind the server to"""

    port: int = 8000
    """Port to listen on"""

    workers: Literal[1] = 1
    """Number of uvicorn worker processes."""

    log_level: Literal["debug", "info", "warning", "error", "critical"] = "info"
    """Uvicorn log level"""

    access_log: bool = True
    """Enable uvicorn access log"""

    @field_validator("cors_origin", mode="before")
    @classmethod
    def _cors_processor(cls, v):
        if isinstance(v, str):
            return [origin for origin in v.split(",") if origin]
        return v

    @field_validator("cors_origin")
    @classmethod
    def _cors_no_wildcard(cls, v: list[str]) -> list[str]:
        if "*" in v:
            raise ValueError(
                "cors_origin cannot contain '*': the session cookie needs credentialed CORS"
            )
        return v


class ChatSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    max_message_chars: int = 2000
    """Maximum characters of a user message"""

    max_turns: int = Field(default=20, gt=0)
    """Max conversation turns sent to model as context"""


class ModelSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    provider: Provider
    """Model adapter; openai_compatible reaches any other OpenAI-compatible API"""

    model: str
    """Provider model name, e.g. openai/gpt-oss-120b"""

    base_url: HttpUrl | None = None
    """API base URL, required for openai_compatible"""

    api_key_env: str | None = None
    """Environment variable holding the API key, defaulting to the provider's
    own (e.g. GROQ_API_KEY); required for openai_compatible"""

    temperature: float | None = None
    """Sampling temperature, the provider default when unset"""

    max_tokens: int | None = Field(default=None, gt=0)
    """Maximum tokens per response, the provider default when unset"""

    timeout_s: float = Field(default=30, gt=0)
    """Request timeout in seconds"""

    max_retries: int = Field(default=1, ge=0)
    """Retries before falling back to the next model"""


class LLMSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    models: tuple[ModelSettings, ...] = ()
    """Chat models in fallback order. A model whose API key is missing is
    skipped; ezbot refuses to start if none is left."""


class SessionSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    cookie_name: str = "ezbot_cookie"
    """Name of the HttpOnly cookie, shared by every tab of a browser and
    kept until the browser closes"""

    cookie_secure: bool = True
    """Send the cookie over HTTPS only; disable for plain-HTTP local dev"""

    cookie_same_site: Literal["lax", "strict", "none"] = "lax"
    """Cookie SameSite policy. lax needs the frontend and API on the same site"""

    session_header: str = "X-Ezbot-Session"
    """Header carrying the tab's session id; each tab has its own session"""

    idle_ttl_s: int = Field(default=900, gt=0)
    """Seconds without activity before a session and its history are deleted"""

    max_sessions: int = Field(default=2000, gt=0)
    """Live sessions kept in memory; new sessions are refused beyond this, live
    ones are never evicted"""

    sweep_interval_s: int = Field(default=60, gt=0)
    """Seconds between sweeps for expired sessions"""


class RateLimitSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    window_s: int = Field(default=600, gt=0)
    """Sliding window in seconds for the burst limits below"""

    max_messages_per_cookie: int = Field(default=10, gt=0)
    """Chat messages per window from one cookie, across all its tabs"""

    max_messages_per_ip: int = Field(default=20, gt=0)
    """Chat messages per window from one client IP"""

    max_daily_messages_per_ip: int = Field(default=50, gt=0)
    """Chat messages from one client IP in any rolling 24 hours"""

    client_ip_header: str | None = None
    """Header with the real client IP when behind a proxy, e.g.
    cf-connecting-ip behind a Cloudflare Tunnel; the socket address when unset"""


class StreamSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    retry_ms: int = Field(default=2000, gt=0)
    """Reconnection delay hint sent to the client with the first event"""

    replay_ttl_s: int = Field(default=60, gt=0)
    """Seconds a finished response stays resumable after its last event"""


class IntentSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    enabled: bool = False
    """Classify which portfolio section a message asks for with Laya"""

    url: HttpUrl | None = None
    """Base URL of the Laya server, e.g. http://localhost:8001"""

    model: str = "multilingual"
    """Laya checkpoint to ask"""

    timeout_s: float = Field(default=10, gt=0)
    """Seconds to wait for a decision before showing no button"""

    context: int = Field(default=3, gt=0)
    """Recent messages, the latest included, given to Laya as the conversation
    window"""

    latest_message_threshold: float = Field(default=0.8, ge=0, le=1)
    """Latest message threshold to display navigation button. If not met threshold
    will make the final decision"""

    threshold: float = Field(default=0.5, ge=0, le=1)
    """Confidence by consolidating all messages within context window 
    to decide if navigation button is shown"""

    @model_validator(mode="after")
    def _enabled_requires_url(self) -> IntentSettings:
        if self.enabled and self.url is None:
            raise ValueError("intent.enabled is True but intent.url is not set")
        return self


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
    llm: LLMSettings = Field(default_factory=LLMSettings)
    session: SessionSettings = Field(default_factory=SessionSettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    stream: StreamSettings = Field(default_factory=StreamSettings)
    intent: IntentSettings = Field(default_factory=IntentSettings)
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
    "IntentSettings",
    "LLMSettings",
    "ModelSettings",
    "ObservabilitySettings",
    "RateLimitSettings",
    "SessionSettings",
    "Settings",
    "StreamSettings",
    "TraceRedactionSettings",
    "get_settings",
    "reload_settings",
]
