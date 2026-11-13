from cryptography.fernet import Fernet
from sqlalchemy import select

from src.core.config import reload_settings
from src.core.providers import Provider
from src.features.connections import Connection
from tests.conftest import JSEARCH_ENCRYPTION_KEY, PREFIX

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


async def test_a_removed_jsearch_key_shows_as_not_connected(client):
    await client.put(JSEARCH, json={"api_key": API_KEY})

    removed = await client.delete(JSEARCH)

    assert removed.status_code == 200
    assert _jsearch(removed.json()) == {
        "id": "jsearch",
        "status": "not_connected",
        "quota": None,
        "account": None,
    }


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
