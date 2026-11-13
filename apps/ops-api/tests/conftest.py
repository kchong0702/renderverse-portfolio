import json
import os
import re
from base64 import b64encode, urlsafe_b64encode
from collections.abc import AsyncIterator, Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from dependency_injector import providers
from fastapi import FastAPI
from pydantic import JsonValue
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response

if TYPE_CHECKING:
    from src.clients.storage import LocalStorage

PREFIX = "/ops-api/v1"
OWNER = "owner@example.com"
JSEARCH_ENCRYPTION_KEY = "pcmpLWT8lLZJmPF7IsUqBimTLFLTgPGcQmjx82jBz9M="
ENCRYPTION_KEY = urlsafe_b64encode(b"e" * 32).decode()
GOOGLE_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly "
    "https://www.googleapis.com/auth/gmail.send "
    "https://www.googleapis.com/auth/calendar.readonly "
    "https://www.googleapis.com/auth/calendar.events"
)


def pytest_configure(config: pytest.Config) -> None:
    """Pin the settings tests rely on before any app module reads them"""
    os.environ["OPS_API_AUTH__ENABLED"] = "false"
    os.environ["OPS_API_EZCAREER__URL"] = "http://harness.test/ezcareer"
    os.environ["OPS_API_EZCAREER__STORES"] = "memory"
    os.environ["OPS_API_ARTIFACT__URL"] = "http://artifact.test/artifact-service"
    os.environ["OPS_API_JSEARCH__ENCRYPTION_KEY"] = JSEARCH_ENCRYPTION_KEY
    os.environ["OPS_API_JSEARCH__RETRY_MAX_WAIT_SECONDS"] = "0"
    os.environ["OPS_API_GOOGLE__CLIENT_ID"] = "client.test"
    os.environ["OPS_API_GOOGLE__CLIENT_SECRET"] = "client-secret"
    os.environ["OPS_API_GOOGLE__ENCRYPTION_KEY"] = ENCRYPTION_KEY
    os.environ["OPS_API_PORTFOLIO__SITE_URL"] = ""


class FakeProvider:
    """Stands in for Google or GitHub: redirects nowhere, returns a set identity"""

    def __init__(self, subject: str, emails: list[str]):
        from src.adapters.oauth_providers import OAuthIdentity

        self.identity = OAuthIdentity(subject=subject, emails=emails)
        self.fails = False
        self.redirect_uri: str | None = None

    async def authorize_redirect(self, request: Request, redirect_uri: str) -> Response:
        self.redirect_uri = redirect_uri
        return RedirectResponse("https://provider.test/authorize")

    async def fetch_identity(self, request: Request):
        from src.adapters.oauth_providers import OAuthFailed

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
        self.failing = False
        self.outcomes: list[dict | list[dict] | Callable[[dict], dict]] = []
        self.received: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        """Serve the model catalog and answer each A2A POST with the next outcome, a
        list streaming as SSE and a function of the request computing it, or refuse
        to connect when down"""
        if self.down:
            raise httpx2.ConnectError("connection refused", request=request)
        if request.method == "GET" and request.url.path == "/ezcareer/models":
            return httpx2.Response(200, json=self.catalog)
        if request.method == "POST" and request.url.path.startswith("/ezcareer/a2a/"):
            self.received.append(request)
            rpc_id = json.loads(request.content)["id"]
            outcome = self.outcomes.pop(0)
            if callable(outcome):
                outcome = outcome(json.loads(request.content))
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
        self.failing = False

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


class FakeJSearch:
    def __init__(self):
        """One job, a quota of 180 of 200 and status 200 until a test changes them"""
        self.jobs: list[dict] = [
            {
                "job_id": "js-1",
                "job_title": "Backend Engineer",
                "employer_name": "Acme",
                "job_apply_link": "https://jobs.example.com/1",
            }
        ]
        self.headers = {
            "x-ratelimit-requests-remaining": "180",
            "x-ratelimit-requests-limit": "200",
        }
        self.status = 200
        self.received: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        """Answer each search with status, or with jobs as its one page and the
        rate-limit headers"""
        self.received.append(request)
        if self.status != 200:
            return httpx2.Response(self.status)
        return httpx2.Response(
            200,
            headers=self.headers,
            json={"data": {"jobs": self.jobs, "cursor": None}},
        )


class FakeGoogle:
    """Stands in for Google's token endpoint, Gmail and Calendar"""

    def __init__(self):
        self.scope = GOOGLE_SCOPES
        self.revoked = False
        self.down = False
        self.failing = False
        self.refreshed_with: list[str] = []
        self.revoked_tokens: list[str] = []
        self.gmail_queries: list[str] = []
        self.thread_searches: list[dict[str, list[str]]] = []
        self.calendar_params: list[dict[str, list[str]]] = []
        self.messages: dict[str, dict[str, object]] = {}
        self.deleted: list[str] = []
        self.events: list[dict[str, object]] = []
        self.time_zone = "Asia/Kuala_Lumpur"
        self.read_only = False
        self.sent: list[dict[str, str]] = []
        self.created: list[dict[str, object]] = []

    def _token(self, form: dict[str, list[str]]) -> httpx2.Response:
        """A code always works; a refresh works until the grant is revoked"""
        if form["grant_type"] == ["authorization_code"]:
            return httpx2.Response(
                200,
                json={
                    "access_token": "access-1",
                    "refresh_token": "refresh-1",
                    "scope": self.scope,
                },
            )
        if self.revoked:
            return httpx2.Response(400, json={"error": "invalid_grant"})
        self.refreshed_with += form["refresh_token"]
        return httpx2.Response(200, json={"access_token": "access-2"})

    def _matches(self, message: dict, search: str) -> bool:
        """Whether a message matches every term of a Gmail search as Ops writes one"""
        payload = message["payload"]
        header = {h["name"]: h["value"] for h in payload["headers"]}
        sent = datetime.fromtimestamp(int(message["internalDate"]) / 1000, UTC).date()
        for negated, operator, quoted, bare in re.findall(
            r'(-?)(?:(\w+):)?(?:"([^"]*)"|(\S+))', search
        ):
            value = (quoted or bare).lower()
            match operator:
                case "after":
                    found = sent >= date(*map(int, value.split("/")))
                case "before":
                    found = sent < date(*map(int, value.split("/")))
                case "from":
                    found = value in header["From"].lower()
                case "has":
                    found = any(p.get("filename") for p in payload.get("parts", []))
                case _:
                    found = value in f"{header['Subject']} {message['snippet']}".lower()
            if found == bool(negated):
                return False
        return True

    def _write(self, request: httpx2.Request) -> httpx2.Response:
        """Send an email or add an event as Google does unless the grant is read-only"""
        if self.read_only:
            return httpx2.Response(
                403, json={"error": {"errors": [{"reason": "insufficientPermissions"}]}}
            )
        body = json.loads(request.content)
        if request.url.path == "/gmail/v1/users/me/messages/send":
            self.sent.append(body)
            return httpx2.Response(200, json={"id": f"sent-{len(self.sent)}"})
        if "id" in body and not re.fullmatch("[a-v0-9]{5,1024}", body["id"]):
            return httpx2.Response(
                400, json={"error": {"errors": [{"reason": "invalid"}]}}
            )
        if "id" in body and body["id"] in [e.get("id") for e in self.created]:
            return httpx2.Response(
                409,
                json={
                    "error": {
                        "code": 409,
                        "message": "The requested identifier already exists.",
                        "errors": [
                            {
                                "domain": "global",
                                "reason": "duplicate",
                                "message": "The requested identifier already exists.",
                            }
                        ],
                    }
                },
            )
        self.created.append(body)
        return httpx2.Response(
            200,
            json={"id": f"event-{len(self.created)}", "status": "confirmed", **body},
        )

    def _change(self, request: httpx2.Request) -> httpx2.Response:
        """Move or delete an added event as Google does; a deleted one keeps its id"""
        event_id = request.url.path.rsplit("/", 1)[1]
        event = next((e for e in self.created if e.get("id") == event_id), None)
        if event is None:
            return httpx2.Response(404)
        if request.method == "DELETE":
            if event.get("status") == "cancelled":
                return httpx2.Response(410)
            event["status"] = "cancelled"
            return httpx2.Response(204)
        event |= json.loads(request.content)
        return httpx2.Response(200, json=event)

    def _api(self, request: httpx2.Request) -> httpx2.Response:
        """Gmail and Calendar for a request that carries an access token"""
        if self.failing:
            return httpx2.Response(500, text="backend detail for Google's engineers")
        if request.method == "POST":
            return self._write(request)
        if request.method in ("PATCH", "DELETE"):
            return self._change(request)
        path = request.url.path
        query = parse_qs(urlsplit(str(request.url)).query, keep_blank_values=True)
        if path == "/gmail/v1/users/me/profile":
            return httpx2.Response(200, json={"emailAddress": "kelvin@gmail.com"})
        if path == "/gmail/v1/users/me/messages":
            self.gmail_queries += query["q"]
            refs = [
                {"id": key, "threadId": f"t-{key}"}
                for key in [*self.messages, *self.deleted]
            ]
            return httpx2.Response(200, json={"messages": refs} if refs else {})
        if path == "/gmail/v1/users/me/threads":
            self.thread_searches.append(query)
            threads: dict[str, list[dict]] = {}
            for message in self.messages.values():
                threads.setdefault(str(message["threadId"]), []).append(message)
            found = [
                {"id": thread_id}
                for thread_id, messages in threads.items()
                if any(self._matches(m, query["q"][0]) for m in messages)
            ]
            return httpx2.Response(
                200,
                json={
                    "threads": found[: int(query["maxResults"][0])],
                    "resultSizeEstimate": len(found),
                }
                if found
                else {"resultSizeEstimate": 0},
            )
        if path.startswith("/gmail/v1/users/me/threads/"):
            thread_id = path.rsplit("/", 1)[1]
            messages = [m for m in self.messages.values() if m["threadId"] == thread_id]
            return (
                httpx2.Response(200, json={"id": thread_id, "messages": messages[::-1]})
                if messages
                else httpx2.Response(404)
            )
        if path.startswith("/gmail/v1/users/me/messages/"):
            message = self.messages.get(path.rsplit("/", 1)[1])
            return (
                httpx2.Response(200, json=message) if message else httpx2.Response(404)
            )
        if path == "/calendar/v3/calendars/primary/events":
            self.calendar_params.append(query)
            return httpx2.Response(
                200, json={"timeZone": self.time_zone, "items": self.events}
            )
        return httpx2.Response(404)

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        """Route a request the way Google's hosts would"""
        if self.down:
            raise httpx2.ConnectError("connection refused", request=request)
        if request.url.path == "/token":
            return self._token(parse_qs(request.content.decode()))
        if request.url.path == "/revoke":
            self.revoked_tokens += parse_qs(request.content.decode())["token"]
            return httpx2.Response(200)
        if request.headers.get("authorization", "").startswith("Bearer access-"):
            return self._api(request)
        return httpx2.Response(401, content=json.dumps({"error": "unauthorized"}))


async def work(app: FastAPI) -> None:
    """Claim and process imports and job runs until none is due"""
    from src.db.queue import claim
    from src.worker import QUEUES

    for queue, process in QUEUES:
        while True:
            async with app.state.session_factory() as session, session.begin():
                claimed = await claim(session, queue, timedelta(seconds=60))
            if claimed is None:
                break
            await process(claimed.id, claimed.claim_token, app.state.container)


async def idle_in_transaction() -> int:
    """How many connections to the test Postgres database sit idle inside a
    transaction"""
    from tests.core.conftest import DATABASE_URL

    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    async with engine.connect() as db:
        count = await db.scalar(
            text(
                "SELECT count(*) FROM pg_stat_activity"
                " WHERE datname = current_database()"
                " AND state = 'idle in transaction'"
            )
        )
    await engine.dispose()
    return count


async def connect_google(client: httpx2.AsyncClient, next_path: str = "/settings"):
    """Run the connect flow against FakeGoogle and return the callback's response"""
    start = await client.get(
        f"{PREFIX}/integrations/google/connect", params={"next": next_path}
    )
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    return await client.get(
        f"{PREFIX}/integrations/google/callback",
        params={"code": "code-1", "state": state},
    )


async def _app(
    harness: FakeHarness,
    artifact: FakeArtifact,
    google: FakeGoogle,
    jsearch: FakeJSearch,
    storage: "LocalStorage",
    oauth_providers: dict | None = None,
    engine: AsyncEngine | None = None,
) -> AsyncIterator[FastAPI]:
    from src.adapters.job_sources.jsearch import JSearchSource
    from src.app.app import create_app
    from src.app.container import Container
    from src.clients.artifact import ArtifactClient
    from src.clients.ezcareer import EzcareerClient
    from src.clients.google import GoogleClient
    from src.core.config import reload_settings
    from src.core.stores import UsageLedger
    from src.db.base import Base
    from src.db.session import create_session_factory

    settings = reload_settings()
    directory = TemporaryDirectory()
    engine = engine or create_async_engine(
        f"sqlite+aiosqlite:///{directory.name}/ops.db"
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
    container.storage.override(providers.Object(storage))
    container.ezcareer.override(
        providers.Object(
            EzcareerClient(
                settings.ezcareer,
                UsageLedger(session_factory, settings.ezcareer).record,
                httpx2.MockTransport(harness),
            )
        )
    )
    container.google.override(
        providers.Object(GoogleClient(settings.google, httpx2.MockTransport(google)))
    )
    container.job_source.override(
        providers.Object(JSearchSource(settings.jsearch, httpx2.MockTransport(jsearch)))
    )

    yield create_app(container)
    await engine.dispose()
    directory.cleanup()


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
def google() -> FakeGoogle:
    return FakeGoogle()


@pytest.fixture
def jsearch() -> FakeJSearch:
    """JSearch as the test app reaches it"""
    return FakeJSearch()


@pytest.fixture
def storage(tmp_path: Path) -> "LocalStorage":
    """Local storage with public files under tmp_path/public, uploads under private"""
    from src.clients.storage import LocalStorage

    return LocalStorage(
        tmp_path / "public", tmp_path / "private", "/ops-api/v1/portfolio/uploads"
    )


@pytest.fixture
async def app(
    harness: FakeHarness,
    artifact: FakeArtifact,
    google: FakeGoogle,
    jsearch: FakeJSearch,
    storage: "LocalStorage",
) -> AsyncIterator[FastAPI]:
    """Auth disabled: every request is auth.dev_email"""
    async for app in _app(harness, artifact, google, jsearch, storage):
        yield app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx2.AsyncClient]:
    async with _client(app) as http:
        yield http


@pytest.fixture
async def postgres_app(
    harness: FakeHarness,
    artifact: FakeArtifact,
    google: FakeGoogle,
    jsearch: FakeJSearch,
    storage: "LocalStorage",
) -> AsyncIterator[FastAPI]:
    """The app on the test Postgres database, its dev user deleted after the test"""
    from src.core.auth.models import User
    from src.core.config import get_settings
    from tests.core.conftest import DATABASE_URL

    async for app in _app(
        harness,
        artifact,
        google,
        jsearch,
        storage,
        engine=create_async_engine(DATABASE_URL),
    ):
        yield app
        async with app.state.session_factory() as session, session.begin():
            await session.execute(
                delete(User).where(User.email == get_settings().auth.dev_email)
            )


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
    google: FakeGoogle,
    jsearch: FakeJSearch,
    storage: "LocalStorage",
) -> AsyncIterator[FastAPI]:
    """Auth enabled, OWNER seeded as a user, fake Google and GitHub"""
    from src.core.auth.models import User

    monkeypatch.setenv("OPS_API_AUTH__ENABLED", "true")
    monkeypatch.setenv("OPS_API_AUTH__SECRET_KEY", "k" * 32)
    async for app in _app(harness, artifact, google, jsearch, storage, oauth_providers):
        async with app.state.session_factory() as session, session.begin():
            session.add(User(email=OWNER))
        yield app


@pytest.fixture
async def auth_client(auth_app: FastAPI) -> AsyncIterator[httpx2.AsyncClient]:
    async with _client(auth_app) as http:
        yield http
