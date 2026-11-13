import json
import re
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import update

from src.core.auth.enums import Role
from src.core.auth.models import User
from src.core.auth.service import AuthService
from src.core.config import get_settings, reload_settings
from src.features.portfolio.router import router as portfolio_router
from tests.conftest import OWNER, PREFIX

PORTFOLIO = f"{PREFIX}/portfolio"
PROFILE = f"{PREFIX}/profile"


async def _project(client, title, **fields):
    return (
        await client.post(
            f"{PROFILE}/entries", json={"kind": "project", "title": title, **fields}
        )
    ).json()


async def _seed(client):
    await client.patch(
        PROFILE,
        json={
            "name": "Kelvin Chong",
            "headline": "Senior Software Engineer",
            "location": "Kuala Lumpur",
            "email": "kelvin@example.com",
            "phone": "+60 12 345 6789",
            "links": [{"label": "GitHub", "url": "https://github.com/kchong0702"}],
            "summary": "Builds platforms.",
        },
    )
    python = (
        await client.post(
            f"{PROFILE}/skills", json={"name": "Python", "group": "Languages"}
        )
    ).json()
    perl = (
        await client.post(f"{PROFILE}/skills", json={"name": "Perl", "archived": True})
    ).json()
    renderverse = await _project(
        client,
        "Renderverse",
        summary="3D portfolio you can walk through",
        start="2025-01",
        end="present",
        highlights=["Built the 3D scene."],
        link="https://kelvinchong.dev",
        code_link="https://github.com/kchong0702/renderverse-portfolio",
        tools=["React", "Three.js"],
        on_site=True,
    )
    await _project(client, "Kubernetes migration")
    capstone = await _project(client, "Capstone", on_site=True, archived=True)
    await client.post(
        f"{PROFILE}/entries",
        json={"kind": "role", "title": "Senior Engineer", "on_site": True},
    )
    return python, perl, renderverse, capstone


def _current_file(tmp_path) -> Path:
    (path,) = (tmp_path / "public").glob("sites/*/release/current.json")
    return path


def _current(tmp_path) -> dict:
    return json.loads(_current_file(tmp_path).read_bytes())


async def test_publish_writes_the_draft_as_the_live_release(client, tmp_path):
    python, perl, renderverse, capstone = await _seed(client)

    draft = (await client.get(f"{PORTFOLIO}/draft")).json()
    assert draft["number"] == 1
    assert draft["site_url"] is None
    assert [(c["kind"], c["id"], c["change"]) for c in draft["changes"]] == [
        ("about", None, "changed"),
        ("skill", perl["id"], "added"),
        ("skill", python["id"], "added"),
        ("project", renderverse["id"], "added"),
        ("project", capstone["id"], "added"),
    ], "the site ignores whether the agents use a skill or project"

    published = await client.post(f"{PORTFOLIO}/releases")

    assert published.status_code == 201
    assert published.json()["number"] == 1
    assert published.json()["live"] is True
    current = _current(tmp_path)
    assert current["number"] == 1
    assert current["about"] == {
        "name": "Kelvin Chong",
        "headline": "Senior Software Engineer",
        "summary": "Builds platforms.",
        "location": "Kuala Lumpur",
        "links": [{"label": "GitHub", "url": "https://github.com/kchong0702"}],
    }, "contact details stay off the site"
    assert current["skills"] == [
        {"id": perl["id"], "name": "Perl", "group": ""},
        {"id": python["id"], "name": "Python", "group": "Languages"},
    ]
    assert current["projects"] == [
        {
            "id": renderverse["id"],
            "title": "Renderverse",
            "organisation": "",
            "start": "2025-01",
            "end": "present",
            "summary": "3D portfolio you can walk through",
            "highlights": ["Built the 3D scene."],
            "link": "https://kelvinchong.dev",
            "code_link": "https://github.com/kchong0702/renderverse-portfolio",
            "tools": ["React", "Three.js"],
            "image": None,
            "video": None,
        },
        {
            "id": capstone["id"],
            "title": "Capstone",
            "organisation": "",
            "start": None,
            "end": None,
            "summary": "",
            "highlights": [],
            "link": None,
            "code_link": None,
            "tools": [],
            "image": None,
            "video": None,
        },
    ]
    assert (await client.get(f"{PORTFOLIO}/draft")).json()["changes"] == []


async def test_publish_needs_a_change_since_the_live_release(client):
    _, _, renderverse, _ = await _seed(client)
    await client.post(f"{PORTFOLIO}/releases")

    assert (await client.post(f"{PORTFOLIO}/releases")).status_code == 409

    await client.put(
        f"{PROFILE}/entries/{renderverse['id']}",
        json={"title": "Renderverse", "on_site": False},
    )
    draft = (await client.get(f"{PORTFOLIO}/draft")).json()
    assert draft["number"] == 2
    assert draft["changes"] == [
        {
            "kind": "project",
            "id": renderverse["id"],
            "name": "Renderverse",
            "change": "removed",
        }
    ]
    assert (await client.post(f"{PORTFOLIO}/releases")).json()["number"] == 2


async def test_rolling_back_serves_an_earlier_release_and_can_be_undone(
    client, tmp_path
):
    await _seed(client)
    first = (await client.post(f"{PORTFOLIO}/releases")).json()
    kotlin = (await client.post(f"{PROFILE}/skills", json={"name": "Kotlin"})).json()
    second = (await client.post(f"{PORTFOLIO}/releases")).json()

    rolled = await client.post(f"{PORTFOLIO}/releases/{first['id']}/live")

    assert rolled.json()["live"] is True
    assert _current(tmp_path)["number"] == 1
    assert [
        (r["number"], r["live"])
        for r in (await client.get(f"{PORTFOLIO}/releases")).json()
    ] == [
        (2, False),
        (1, True),
    ]
    draft = (await client.get(f"{PORTFOLIO}/draft")).json()
    assert draft["number"] == 3
    assert [(c["id"], c["change"]) for c in draft["changes"]] == [
        (kotlin["id"], "added")
    ]

    await client.post(f"{PORTFOLIO}/releases/{second['id']}/live")
    assert _current(tmp_path)["number"] == 2
    assert (await client.get(f"{PORTFOLIO}/draft")).json()["changes"] == []


async def test_nothing_is_published_when_storage_fails(client, tmp_path):
    await _seed(client)
    first = (await client.post(f"{PORTFOLIO}/releases")).json()
    await client.post(f"{PROFILE}/skills", json={"name": "Kotlin"})
    _current_file(tmp_path).chmod(0o444)

    assert (await client.post(f"{PORTFOLIO}/releases")).status_code == 503

    releases = (await client.get(f"{PORTFOLIO}/releases")).json()
    assert [(r["number"], r["live"]) for r in releases] == [(1, True)]
    assert _current(tmp_path)["number"] == first["number"]


async def test_rolling_back_needs_a_release_of_the_user(client):
    response = await client.post(f"{PORTFOLIO}/releases/{uuid4()}/live")

    assert response.status_code == 404


async def test_every_portfolio_route_needs_a_session(auth_client):
    for method, path in (
        ("GET", "draft"),
        ("GET", "releases"),
        ("POST", "releases"),
        ("POST", f"releases/{uuid4()}/live"),
    ):
        response = await auth_client.request(method, f"{PORTFOLIO}/{path}")
        assert response.status_code == 401, path


@pytest.mark.parametrize(
    ("role", "forbidden"), [(Role.USER, True), (Role.ADMIN, False)]
)
async def test_only_an_admin_can_use_a_portfolio_route(
    auth_app, auth_client, role, forbidden
):
    async with auth_app.state.session_factory() as session:
        await AuthService(session, get_settings().auth).set_password(OWNER, "p" * 12)
        await session.execute(update(User).values(role=role))
        await session.commit()
    await auth_client.post(
        f"{PREFIX}/auth/password", json={"email": OWNER, "password": "p" * 12}
    )
    values = {"sha256": "0" * 64, "slot": "image"}
    routes = [
        (
            method,
            re.sub(r"{(\w+)}", lambda m: values.get(m[1], str(uuid4())), route.path),
        )
        for route in portfolio_router.routes
        for method in route.methods
    ]

    answers = {
        (method, path): (await auth_client.request(method, f"{PREFIX}{path}", json={}))
        for method, path in routes
    }

    assert len(answers) == 11
    for route, response in answers.items():
        assert (response.status_code == 403) is forbidden, route
        if forbidden:
            assert response.json()["detail"] == "Only the admin can use the portfolio"


async def test_draft_names_the_site_once_its_url_is_set(client, monkeypatch):
    monkeypatch.setenv("OPS_API_PORTFOLIO__SITE_URL", "https://portfolio.example")
    reload_settings()

    draft = (await client.get(f"{PORTFOLIO}/draft")).json()
    settings = (await client.get(f"{PREFIX}/settings")).json()

    assert draft["site_url"] == "https://portfolio.example"
    assert {
        "id": "portfolio_site",
        "status": "connected",
        "quota": None,
        "account": None,
    } in settings["connections"]
