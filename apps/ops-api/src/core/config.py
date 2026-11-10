from __future__ import annotations

from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, override

from cryptography.fernet import Fernet
from dotenv import load_dotenv
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

_APP_NAME = "ops-api"

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
    """Execution environment"""

    version: str = "0.1.0"
    """Application's version"""

    cors_origin: Annotated[list[str], NoDecode] = ["*"]
    """Cors origins"""

    route_prefix: str = "/ops-api"
    """FastAPI router prefix, matching the `tailscale serve` path"""

    host: str = "127.0.0.1"
    """Host address to bind the server to"""

    port: int = 8100
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


class ArtifactSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    url: str = "http://127.0.0.1:8210/artifact-service"
    """artifact-service base URL, including its route prefix"""

    timeout_seconds: float = Field(default=60, gt=0)
    """How long a request may take; a render can take 30 seconds"""


class DocumentsSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    max_per_kind: int = Field(default=10, gt=0)
    """How many résumés, CVs or cover letters a user keeps at most, each"""

    match_cutoff: int = Field(default=70, ge=0, le=100)
    """How closely, from 0 to 100, a title must match the name a run asks for"""

    max_upload_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    """The largest résumé file a user may upload"""

    upload_types: frozenset[str] = frozenset(
        {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
    )
    """The media types an uploaded résumé may have: PDF or Word"""


class OAuthClientSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    client_id: str = ""
    """OAuth client id; the provider is offered only when it is set"""

    client_secret: SecretStr = SecretStr("")
    """OAuth client secret"""

    scope: str
    """Space-separated scopes asked for at sign-in"""

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret.get_secret_value())


class GoogleOAuthSettings(OAuthClientSettings):
    discovery_url: str = "https://accounts.google.com/.well-known/openid-configuration"
    """OpenID Connect discovery document; Authlib reads the endpoints and keys from it"""

    scope: str = "openid email"
    """The ID token's subject and verified email"""


class GitHubOAuthSettings(OAuthClientSettings):
    authorize_url: str = "https://github.com/login/oauth/authorize"
    """Where the user is sent to approve the sign-in"""

    access_token_url: str = "https://github.com/login/oauth/access_token"
    """Where the callback's code is exchanged for an access token"""

    api_base_url: str = "https://api.github.com/"
    """Where the user and user/emails endpoints are read from"""

    scope: str = "read:user user:email"
    """The account id, and its emails with their verified flags"""


class AuthSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    enabled: bool = False
    """Require a signed-in session on every request"""

    allowed_emails: Annotated[list[str], NoDecode] = []
    """Emails allowed to sign in, with a password or a verified SSO email"""

    dev_email: str = "owner@localhost"
    """Who a request acts as while auth is disabled"""

    web_url: str = "http://localhost:5174"
    """Where ops-web is served; OAuth callbacks and redirects go through it"""

    secret_key: SecretStr = SecretStr("")
    """Signs the short-lived OAuth state cookie"""

    session_idle_days: int = Field(default=30, gt=0)
    """A session expires after this many days without a request"""

    google: GoogleOAuthSettings = Field(default_factory=GoogleOAuthSettings)
    """Sign in with Google"""

    github: GitHubOAuthSettings = Field(default_factory=GitHubOAuthSettings)
    """Sign in with GitHub"""

    @field_validator("allowed_emails", mode="before")
    @classmethod
    def _emails_processor(cls, v: object) -> object:
        return _split_csv(v)

    @field_validator("allowed_emails", mode="after")
    @classmethod
    def _normalise_emails(cls, v: list[str]) -> list[str]:
        return [email.lower() for email in v]

    @field_validator("web_url", mode="after")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @model_validator(mode="after")
    def _enabled_requires_allowlist_and_key(self) -> AuthSettings:
        if not self.enabled:
            return self
        if not self.allowed_emails:
            raise ValueError("auth.enabled is True but auth.allowed_emails is empty")
        if len(self.secret_key.get_secret_value()) < 32:
            raise ValueError("auth.enabled needs auth.secret_key of 32+ characters")
        return self

    @property
    def secure_cookies(self) -> bool:
        return self.web_url.startswith("https://")


class DatabaseSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    url: SecretStr = SecretStr("postgresql+asyncpg://ops:ops@localhost:5432/ops")
    """SQLAlchemy async URL; Supabase through the session pooler"""

    pool_size: int = Field(default=5, gt=0)
    """Connection pool size"""

    echo: bool = False
    """Log every SQL statement"""


class ModelPrice(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    provider: str
    """The model's family, such as claude"""

    model: str
    """The model, as ezcareer-harness names it"""

    effective_from: date
    """The first day the price applies"""

    input_per_mtok: Decimal = Field(ge=0)
    """USD per million uncached input tokens"""

    output_per_mtok: Decimal = Field(ge=0)
    """USD per million output tokens"""

    cache_read_per_mtok: Decimal = Field(ge=0)
    """USD per million input tokens read from the prompt cache"""

    cache_write_per_mtok: Decimal = Field(ge=0)
    """USD per million input tokens written to the prompt cache"""


class EzcareerSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    url: str = "http://127.0.0.1:8200/ezcareer"
    """ezcareer-harness base URL, including its route prefix"""

    timeout_seconds: float = Field(default=10, gt=0)
    """How long a request to ezcareer-harness may take"""

    run_timeout_seconds: float = Field(default=300, gt=0)
    """How long an agent or workflow run may take before it pauses or ends"""

    stream_retry_ms: int = Field(default=2000, gt=0)
    """How long a client waits before it reconnects to a broken stream"""

    replay_ttl_seconds: float = Field(default=60, gt=0)
    """How long a finished run can still be resumed"""

    run_poll_seconds: float = Field(default=5, gt=0)
    """How often a reader checks a run it heard nothing about, in case a notification
    was missed"""

    stores: Literal["memory", "postgres"] = "memory"
    """Where agent runs are kept: memory serves one ops-api process, postgres
    lets any process replay and follow them"""

    prices: list[ModelPrice] = []
    """Each model's list prices over time, which cost each model call"""


class JSearchSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    encryption_key: SecretStr = SecretStr("")
    """Fernet key that encrypts stored JSearch API keys; saving a key needs it"""

    @field_validator("encryption_key", mode="after")
    @classmethod
    def _must_be_a_fernet_key(cls, v: SecretStr) -> SecretStr:
        """Fail at startup on a key Fernet cannot use, not on the first save"""
        if v.get_secret_value():
            Fernet(v.get_secret_value())
        return v


class GoogleSettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    client_id: str = ""
    """OAuth client id for reading Gmail and Calendar; connecting Google needs it"""

    client_secret: SecretStr = SecretStr("")
    """OAuth client secret"""

    redirect_uri: str = "http://localhost:5174/ops-api/v1/integrations/google/callback"
    """Where Google sends the user back; must be listed on the OAuth client"""

    encryption_key: SecretStr = SecretStr("")
    """Fernet key that encrypts stored Google refresh tokens; connecting needs it"""

    inbox_query: str = (
        "newer_than:90d -category:promotions -category:social "
        "(subject:(application OR applying OR interview OR offer OR recruiter "
        'OR candidate OR "next steps") '
        "OR from:(greenhouse.io OR lever.co OR ashbyhq.com OR myworkday.com "
        "OR workablemail.com OR smartrecruiters.com))"
    )
    """Gmail search that picks the job-search emails Inbox lists"""

    inbox_limit: int = Field(default=25, gt=0)
    """How many of the newest matching emails Inbox lists"""

    calendar_max_days: int = Field(default=62, gt=0)
    """The longest range Calendar reads in one request"""

    calendar_max_events: int = Field(default=250, gt=0)
    """The most events Calendar asks Google for in one request"""

    interview_minutes: int = Field(default=60, gt=0)
    """How long an interview lasts when its email gives no end; the shortest free
    slot a reply offers"""

    free_slot_days: int = Field(default=7, gt=0)
    """How many days from tomorrow a reply offers free slots in"""

    timeout_seconds: float = Field(default=10, gt=0)
    """How long a request to Google may take"""

    @field_validator("encryption_key", mode="after")
    @classmethod
    def _must_be_a_fernet_key(cls, v: SecretStr) -> SecretStr:
        """Fail at startup on a key Fernet cannot use, not on the first connect"""
        if v.get_secret_value():
            Fernet(v.get_secret_value())
        return v

    @property
    def configured(self) -> bool:
        """Whether the client id, secret and encryption key are all set"""
        return bool(
            self.client_id
            and self.client_secret.get_secret_value()
            and self.encryption_key.get_secret_value()
        )


class ObservabilitySettings(BaseModel):
    model_config = {"extra": "forbid", "frozen": True}

    service_name: str = _APP_NAME
    """Service name every log line is tagged with"""

    log_level: LogLevel = "INFO"
    """Application log level"""

    log_format: LogFormat = "json"
    """Logging format"""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPS_API_",
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
    """Server and HTTP settings"""

    artifact: ArtifactSettings = Field(default_factory=ArtifactSettings)
    """Where ops-api reaches artifact-service for templates and PDFs"""

    documents: DocumentsSettings = Field(default_factory=DocumentsSettings)
    """Limits on the documents a user keeps"""

    auth: AuthSettings = Field(default_factory=AuthSettings)
    """Sign-in and session settings"""

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    """Database connection settings"""

    ezcareer: EzcareerSettings = Field(default_factory=EzcareerSettings)
    """Where ops-api reaches ezcareer-harness"""

    jsearch: JSearchSettings = Field(default_factory=JSearchSettings)
    """Keeping each user's JSearch API key"""

    google: GoogleSettings = Field(default_factory=GoogleSettings)
    """Reading the user's Gmail and Google Calendar"""

    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)
    """Logging settings"""

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
    "ArtifactSettings",
    "AuthSettings",
    "DatabaseSettings",
    "DocumentsSettings",
    "EzcareerSettings",
    "GoogleSettings",
    "JSearchSettings",
    "ObservabilitySettings",
    "Settings",
    "get_settings",
    "reload_settings",
]
