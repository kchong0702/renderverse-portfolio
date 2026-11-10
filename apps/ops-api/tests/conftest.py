import json
import os
from base64 import b64encode
from collections.abc import AsyncIterator

import httpx2
import pytest
from dependency_injector import providers
from fastapi import FastAPI
from pydantic import JsonValue
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
    os.environ["OPS_API_EZCAREER__STORES"] = "memory"
    os.environ["OPS_API_ARTIFACT__URL"] = "http://artifact.test/artifact-service"


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
        """Serve the model catalog and answer each A2A POST with the next outcome, a
        list streaming as SSE, or refuse to connect when down"""
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
            for artifact in (
                outcome.get("result", {}).get("task", {}).get("artifacts", [])
            ):
                artifact.setdefault("name", request.url.path.rsplit("/", 1)[1])
            return httpx2.Response(
                200, json={"jsonrpc": "2.0", "id": rpc_id, **outcome}
            )
        return httpx2.Response(404)


def a2a_task(state: str, *, status_parts=None, artifact_parts=None) -> dict:
    """A SendMessage result as the harness's A2A 1.0 server returns it"""
    task = {
        "id": "task-1",
        "contextId": "context-1",
        "status": {"state": f"TASK_STATE_{state}"},
    }
    if status_parts is not None:
        task["status"]["message"] = {
            "messageId": "m-agent",
            "role": "ROLE_AGENT",
            "parts": status_parts,
        }
    if artifact_parts is not None:
        task["artifacts"] = [{"artifactId": "a-1", "parts": artifact_parts}]
    return {"result": {"task": task}}


def a2a_sent(harness: FakeHarness) -> list[dict]:
    """The A2A requests the harness received, as JSON"""
    return [json.loads(request.content) for request in harness.received]


def stream_task() -> dict:
    """The task SendStreamingMessage sends first"""
    return {
        "result": {
            "task": {
                "id": "task-1",
                "contextId": "context-1",
                "status": {"state": "TASK_STATE_SUBMITTED"},
            }
        }
    }


def stream_status(state: str, parts: list[dict] | None = None) -> dict:
    """A status update of task-1, with a message when parts are given"""
    status: dict = {"state": f"TASK_STATE_{state}"}
    if parts is not None:
        status["message"] = {"messageId": "m", "role": "ROLE_AGENT", "parts": parts}
    return {
        "result": {
            "statusUpdate": {
                "taskId": "task-1",
                "contextId": "context-1",
                "status": status,
            }
        }
    }


def stream_chunk(artifact_id: str, name: str, part: dict) -> dict:
    """An artifact update of task-1"""
    return {
        "result": {
            "artifactUpdate": {
                "taskId": "task-1",
                "contextId": "context-1",
                "artifact": {"artifactId": artifact_id, "name": name, "parts": [part]},
            }
        }
    }


def sse_events(response) -> list[dict]:
    """The run events an SSE response carried"""
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


def sse_ids(response) -> list[str]:
    """The SSE event ids a response carried"""
    return [
        line.removeprefix("id: ")
        for line in response.text.splitlines()
        if line.startswith("id: ")
    ]


class FakeArtifact:
    def __init__(self):
        """One template for every kind; records each render it is asked for"""
        self.templates = [
            {
                "id": "classic",
                "name": "Classic",
                "description": "One column with the name and contacts in a header.",
                "kinds": ["resume", "cv", "cover_letter"],
                "body_font": "source-sans-3",
                "heading_font": "source-serif-4",
                "accent": "#1F3A5F",
                "regions": {"top": {"area": {"row": 1}}, "main": {"area": {"row": 2}}},
                "layout": {"default": "main", "profile": "top"},
            }
        ]
        self.rendered: list[JsonValue] = []
        self.down = False

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        """Serve templates and renders at /artifact-service/v1, or refuse when down"""
        if self.down:
            raise httpx2.ConnectError("connection refused", request=request)
        match request.method, request.url.path:
            case "GET", "/artifact-service/v1/templates":
                kind = request.url.params["kind"]
                return httpx2.Response(
                    200, json=[t for t in self.templates if kind in t["kinds"]]
                )
            case "POST", "/artifact-service/v1/render":
                self.rendered.append(json.loads(request.content))
                pdf = b"%PDF-1.7 \xfb\xff"
                report = {"render_id": "0" * 64, "pages": 1, "last_page_fill": 0.5}
                return httpx2.Response(
                    200, json={"artifact": b64encode(pdf).decode(), "report": report}
                )
        return httpx2.Response(404)


async def _app(
    harness: FakeHarness,
    artifact: FakeArtifact,
    oauth_providers: dict | None = None,
) -> AsyncIterator[FastAPI]:
    from src.app.app import create_app
    from src.app.container import Container
    from src.clients.artifact import ArtifactClient
    from src.clients.ezcareer import EzcareerClient
    from src.core.config import reload_settings
    from src.core.stores import UsageLedger
    from src.db.base import Base
    from src.db.session import create_session_factory

    settings = reload_settings()
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = create_session_factory(engine)
    container = Container()
    container.engine.override(providers.Object(engine))
    container.session_factory.override(providers.Object(session_factory))
    container.oauth_providers.override(providers.Object(oauth_providers or {}))
    container.artifact.override(
        providers.Object(
            ArtifactClient(settings.artifact, httpx2.MockTransport(artifact))
        )
    )
    container.ezcareer.override(
        providers.Object(
            EzcareerClient(
                settings.ezcareer,
                UsageLedger(session_factory, settings.ezcareer).record,
                httpx2.MockTransport(harness),
            )
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
def artifact() -> FakeArtifact:
    """artifact-service as the test app reaches it"""
    return FakeArtifact()


@pytest.fixture
async def app(harness: FakeHarness, artifact: FakeArtifact) -> AsyncIterator[FastAPI]:
    """Auth disabled: every request is auth.dev_email"""
    async for app in _app(harness, artifact):
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
    artifact: FakeArtifact,
) -> AsyncIterator[FastAPI]:
    """Auth enabled, OWNER allowlisted, fake Google and GitHub"""
    monkeypatch.setenv("OPS_API_AUTH__ENABLED", "true")
    monkeypatch.setenv("OPS_API_AUTH__ALLOWED_EMAILS", OWNER)
    monkeypatch.setenv("OPS_API_AUTH__SECRET_KEY", "k" * 32)
    async for app in _app(harness, artifact, oauth_providers):
        yield app


@pytest.fixture
async def auth_client(auth_app: FastAPI) -> AsyncIterator[httpx2.AsyncClient]:
    async with _client(auth_app) as http:
        yield http
