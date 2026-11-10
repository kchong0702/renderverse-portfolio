import json
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
    os.environ["OPS_API_EZCAREER__URL"] = "http://harness.test/ezcareer"


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


class FakeHarness:
    def __init__(self):
        self.catalog = {
            "families": [
                {"family": "claude", "models": ["claude-sonnet-4-5"]},
                {"family": "openai", "models": ["gpt-5", "gpt-5-mini"]},
            ]
        }
        self.down = False
        self.outcomes: list[dict | list[dict]] = []
        self.received: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        """Serve the catalog at GET /ezcareer/models and answer each A2A POST with
        the next of outcomes, a list streaming as SSE, or refuse to connect when down"""
        if self.down:
            raise httpx2.ConnectError("connection refused", request=request)
        if request.method == "GET" and request.url.path == "/ezcareer/models":
            return httpx2.Response(200, json=self.catalog)
        if request.method == "POST" and request.url.path.startswith("/ezcareer/a2a/"):
            self.received.append(request)
            rpc_id = json.loads(request.content)["id"]
            outcome = self.outcomes.pop(0)
            if isinstance(outcome, list):
                return httpx2.Response(
                    200,
                    headers={"content-type": "text/event-stream"},
                    content="".join(
                        f"data: {json.dumps({'jsonrpc': '2.0', 'id': rpc_id, **e})}\n\n"
                        for e in outcome
                    ),
                )
            return httpx2.Response(
                200, json={"jsonrpc": "2.0", "id": rpc_id, **outcome}
            )
        return httpx2.Response(404)


async def _app(
    harness: FakeHarness, oauth_providers: dict | None = None
) -> AsyncIterator[FastAPI]:
    from src.app.app import create_app
    from src.app.container import Container
    from src.core.config import reload_settings
    from src.db import models  # noqa: F401
    from src.db.base import Base
    from src.db.session import create_session_factory
    from src.integrations.ezcareer import EzcareerClient

    settings = reload_settings()
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
    container.ezcareer.override(
        providers.Object(
            EzcareerClient(settings.ezcareer, httpx2.MockTransport(harness))
        )
    )

    yield create_app(container)
    await engine.dispose()


def _client(app: FastAPI) -> httpx2.AsyncClient:
    return httpx2.AsyncClient(
        transport=httpx2.ASGITransport(app=app), base_url="http://test"
    )


@pytest.fixture
def harness() -> FakeHarness:
    return FakeHarness()


@pytest.fixture
async def app(harness: FakeHarness) -> AsyncIterator[FastAPI]:
    """Auth disabled: every request is auth.dev_email"""
    async for app in _app(harness):
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
    monkeypatch: pytest.MonkeyPatch,
    oauth_providers: dict[str, FakeProvider],
    harness: FakeHarness,
) -> AsyncIterator[FastAPI]:
    """Auth enabled, OWNER allowlisted, fake Google and GitHub"""
    monkeypatch.setenv("OPS_API_AUTH__ENABLED", "true")
    monkeypatch.setenv("OPS_API_AUTH__ALLOWED_EMAILS", OWNER)
    monkeypatch.setenv("OPS_API_AUTH__SECRET_KEY", "k" * 32)
    async for app in _app(harness, oauth_providers):
        yield app


@pytest.fixture
async def auth_client(auth_app: FastAPI) -> AsyncIterator[httpx2.AsyncClient]:
    async with _client(auth_app) as http:
        yield http
