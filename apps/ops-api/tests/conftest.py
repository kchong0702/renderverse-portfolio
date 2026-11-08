import os
from collections.abc import AsyncIterator

import httpx2
import pytest
from dependency_injector import providers
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

PREFIX = "/ops-api/v1"
OWNER = "owner@example.com"


def pytest_configure(config: pytest.Config) -> None:
    """Pin the settings tests rely on before any app module reads them"""
    os.environ["OPS_API_AUTH__ENABLED"] = "false"


class FakeProvider:
    """Stands in for Google or GitHub: redirects nowhere, returns a set identity"""

    def __init__(self, subject: str, emails: list[str]):
        from src.core.auth.oauth_providers import OAuthIdentity

        self.identity = OAuthIdentity(subject=subject, emails=emails)
        self.fails = False
        self.redirect_uri: str | None = None

    async def authorize_redirect(self, request: Request, redirect_uri: str) -> Response:
        self.redirect_uri = redirect_uri
        return RedirectResponse("https://provider.test/authorize")

    async def fetch_identity(self, request: Request):
        from src.core.auth.exceptions import OAuthFailed

        if self.fails:
            raise OAuthFailed("access_denied")
        return self.identity


async def _app(oauth_providers: dict | None = None) -> AsyncIterator[FastAPI]:
    from src.app import models  # noqa: F401
    from src.app.app import create_app
    from src.app.container import Container
    from src.core.config import reload_settings
    from src.core.db.base import Base
    from src.core.db.session import create_session_factory

    reload_settings()
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    container = Container()
    container.engine.override(providers.Object(engine))
    container.session_factory.override(providers.Object(create_session_factory(engine)))
    container.oauth_providers.override(providers.Object(oauth_providers or {}))

    yield create_app(container)
    await engine.dispose()


def _client(app: FastAPI) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app), base_url="http://test"
    )


@pytest.fixture
async def app() -> AsyncIterator[FastAPI]:
    """Auth disabled: every request is auth.dev_email"""
    async for app in _app():
        yield app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx2.AsyncClient]:
    async with _client(app) as http:
        yield http


@pytest.fixture
def oauth_providers() -> dict[str, FakeProvider]:
    return {
        "google": FakeProvider("google-1", [OWNER]),
        "github": FakeProvider("github-1", ["other@example.com", OWNER]),
    }


@pytest.fixture
async def auth_app(
    monkeypatch: pytest.MonkeyPatch, oauth_providers: dict[str, FakeProvider]
) -> AsyncIterator[FastAPI]:
    """Auth enabled, OWNER allowlisted, fake Google and GitHub"""
    monkeypatch.setenv("OPS_API_AUTH__ENABLED", "true")
    monkeypatch.setenv("OPS_API_AUTH__ALLOWED_EMAILS", OWNER)
    monkeypatch.setenv("OPS_API_AUTH__SECRET_KEY", "k" * 32)
    async for app in _app(oauth_providers):
        yield app


@pytest.fixture
async def auth_client(auth_app: FastAPI) -> AsyncIterator[httpx2.AsyncClient]:
    async with _client(auth_app) as http:
        yield http
