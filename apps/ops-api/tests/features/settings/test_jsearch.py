import pytest
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


async def test_a_jsearch_key_is_checked_with_one_search_then_stored_encrypted(
    app, client, jsearch
):
    saved = await client.put(JSEARCH, json={"api_key": API_KEY})

    assert saved.status_code == 200
    assert _jsearch(saved.json()) == {
        "id": "jsearch",
        "status": "connected",
        "quota": {"remaining": 180, "limit": 200},
        "account": None,
    }
    [check] = jsearch.received
    assert check.headers["X-RapidAPI-Key"] == API_KEY
    reread = await client.get(SETTINGS)
    assert API_KEY not in saved.text + reread.text
    assert _jsearch(reread.json())["status"] == "connected"
    async with app.state.session_factory() as session:
        stored = await session.scalar(select(Connection))
    assert stored is not None and stored.provider is Provider.JSEARCH
    assert API_KEY.encode() not in stored.secret
    assert Fernet(JSEARCH_ENCRYPTION_KEY).decrypt(stored.secret) == API_KEY.encode()


@pytest.mark.parametrize("status", [401, 403])
async def test_a_key_jsearch_refuses_is_not_stored(client, jsearch, status):
    jsearch.status = status

    response = await client.put(JSEARCH, json={"api_key": API_KEY})

    assert (response.status_code, response.json()["detail"]) == (
        422,
        "JSearch refused the key",
    )
    assert API_KEY not in response.text
    assert _jsearch((await client.get(SETTINGS)).json())["status"] == "not_connected"


async def test_a_key_is_not_stored_when_jsearch_cannot_check_it(client, jsearch):
    jsearch.status = 503

    response = await client.put(JSEARCH, json={"api_key": API_KEY})

    assert (response.status_code, response.json()["detail"]) == (
        503,
        "JSearch answered 503",
    )
    assert _jsearch((await client.get(SETTINGS)).json())["status"] == "not_connected"


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
