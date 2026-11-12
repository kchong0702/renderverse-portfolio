from cryptography.fernet import Fernet
from sqlalchemy import select

from src.core.config import reload_settings
from src.features.connections import Connection, Provider
from tests.conftest import JSEARCH_ENCRYPTION_KEY, PREFIX, a2a_sent, a2a_task, work

SETTINGS = f"{PREFIX}/settings"
JSEARCH = f"{SETTINGS}/connections/jsearch"
API_KEY = "rapidapi-key-1"


def _jsearch(settings: dict) -> dict:
    """The JSearch connection in a settings reply"""
    [connection] = [c for c in settings["connections"] if c["id"] == "jsearch"]
    return connection


async def test_a_jsearch_key_is_stored_encrypted_and_never_returned(app, client):
    saved = await client.put(JSEARCH, json={"api_key": API_KEY})

    assert saved.status_code == 200
    assert _jsearch(saved.json()) == {
        "id": "jsearch",
        "status": "connected",
        "quota": None,
        "account": None,
    }
    reread = await client.get(SETTINGS)
    assert API_KEY not in saved.text + reread.text
    assert _jsearch(reread.json())["status"] == "connected"
    async with app.state.session_factory() as session:
        stored = await session.scalar(select(Connection))
    assert stored is not None and stored.provider is Provider.JSEARCH
    assert API_KEY.encode() not in stored.secret
    assert Fernet(JSEARCH_ENCRYPTION_KEY).decrypt(stored.secret) == API_KEY.encode()


async def test_runs_send_the_jsearch_key_in_metadata(app, client, harness):
    await client.put(JSEARCH, json={"api_key": API_KEY})
    harness.outcomes = [
        a2a_task("COMPLETED", artifact_parts=[{"data": {"jobs": []}}]),
        a2a_task("COMPLETED", artifact_parts=[{"data": {"jobs": []}}]),
    ]
    model = {"family": "claude", "model": "claude-sonnet-4-5"}

    await client.post(f"{PREFIX}/jobs/find")
    await work(app)
    await client.patch(SETTINGS, json={"ai_model": model})
    await client.post(f"{PREFIX}/jobs/find")
    await work(app)

    first, second = a2a_sent(harness)
    assert first["params"]["metadata"] == {"jsearch": {"api_key": API_KEY}}
    assert second["params"]["metadata"] == {
        "model": model,
        "jsearch": {"api_key": API_KEY},
    }
    assert all(
        API_KEY not in str(sent["params"]["message"]) for sent in (first, second)
    )


async def test_a_removed_jsearch_key_is_no_longer_sent(app, client, harness):
    await client.put(JSEARCH, json={"api_key": API_KEY})
    harness.outcomes = [a2a_task("COMPLETED", artifact_parts=[{"data": {"jobs": []}}])]

    removed = await client.delete(JSEARCH)
    await client.post(f"{PREFIX}/jobs/find")
    await work(app)

    assert removed.status_code == 200
    assert _jsearch(removed.json()) == {
        "id": "jsearch",
        "status": "not_connected",
        "quota": None,
        "account": None,
    }
    assert "metadata" not in a2a_sent(harness)[0]["params"]


async def test_the_connection_shows_the_last_find_runs_quota(app, client, harness):
    await client.put(JSEARCH, json={"api_key": API_KEY})
    harness.outcomes = [
        a2a_task(
            "COMPLETED",
            artifact_parts=[
                {"data": {"jobs": [], "quota": {"remaining": 180, "limit": 200}}}
            ],
        ),
        a2a_task(
            "COMPLETED",
            artifact_parts=[
                {"data": {"jobs": [], "quota": {"remaining": 179, "limit": 200}}}
            ],
        ),
    ]

    await client.post(f"{PREFIX}/jobs/find")
    await work(app)
    await client.post(f"{PREFIX}/jobs/find")
    await work(app)

    connection = _jsearch((await client.get(SETTINGS)).json())
    assert connection == {
        "id": "jsearch",
        "status": "connected",
        "quota": {"remaining": 179, "limit": 200},
        "account": None,
    }
    changed = await client.put(JSEARCH, json={"api_key": "rapidapi-key-2"})
    assert _jsearch(changed.json())["quota"] is None


async def test_a_run_on_the_servers_key_shows_no_quota(app, client, harness):
    harness.outcomes = [
        a2a_task(
            "COMPLETED",
            artifact_parts=[
                {"data": {"jobs": [], "quota": {"remaining": 9, "limit": 10}}}
            ],
        )
    ]

    await client.post(f"{PREFIX}/jobs/find")
    await work(app)

    assert _jsearch((await client.get(SETTINGS)).json()) == {
        "id": "jsearch",
        "status": "not_connected",
        "quota": None,
        "account": None,
    }


async def test_an_unreadable_jsearch_key_stops_runs_with_a_clear_error(
    app, client, harness
):
    await client.put(JSEARCH, json={"api_key": API_KEY})
    async with app.state.session_factory() as session:
        stored = await session.scalar(select(Connection))
        assert stored is not None
        stored.secret = Fernet(Fernet.generate_key()).encrypt(b"other")
        await session.commit()

    queued = await client.post(f"{PREFIX}/jobs/find")
    await work(app)

    assert queued.status_code == 202
    failed = (await client.get(f"{PREFIX}/jobs/runs/latest")).json()
    assert failed["status"] == "failed"
    assert "change it in Settings" in failed["error"]
    assert harness.received == []


async def test_a_jsearch_key_needs_the_servers_encryption_key(client, monkeypatch):
    monkeypatch.setenv("OPS_API_JSEARCH__ENCRYPTION_KEY", "")
    reload_settings()

    response = await client.put(JSEARCH, json={"api_key": API_KEY})

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "JSearch keys are not set up on the server: set OPS_API_JSEARCH__ENCRYPTION_KEY"
    )
    assert _jsearch((await client.get(SETTINGS)).json())["status"] == "not_connected"


async def test_an_empty_jsearch_key_is_refused(client):
    response = await client.put(JSEARCH, json={"api_key": ""})

    assert response.status_code == 422
