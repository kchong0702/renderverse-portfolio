import asyncio
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from src.core.auth.dependencies import current_user
from src.core.auth.enums import Role
from src.core.auth.models import User
from src.features.portfolio.models import PortfolioRelease
from tests.conftest import PREFIX, _client
from tests.core.conftest import DATABASE_URL

PORTFOLIO = f"{PREFIX}/portfolio"
PROFILE = f"{PREFIX}/profile"


def _upload(content: bytes, media_type: str, filename: str = "file") -> dict:
    return {
        "sha256": hashlib.sha256(content).hexdigest(),
        "media_type": media_type,
        "size": len(content),
        "filename": filename,
    }


async def _store(client, content: bytes, media_type: str, filename: str = "file"):
    upload = _upload(content, media_type, filename)
    target = (await client.post(f"{PORTFOLIO}/uploads", json=upload)).json()
    put = await client.put(target["url"], content=content, headers=target["headers"])
    assert put.status_code == 204, put.text
    return (await client.post(f"{PORTFOLIO}/assets", json=upload)).json()


async def _project(client, title="Renderverse", kind="project"):
    return (
        await client.post(
            f"{PROFILE}/entries",
            json={"kind": kind, "title": title, "on_site": kind == "project"},
        )
    ).json()


async def _show(client, project, slot, asset):
    return await client.put(
        f"{PORTFOLIO}/projects/{project['id']}/{slot}",
        json={"asset_id": asset and asset["id"]},
    )


def _site(tmp_path) -> Path:
    (site,) = (tmp_path / "public" / "sites").iterdir()
    return site


def _current(tmp_path) -> dict:
    return json.loads((_site(tmp_path) / "release" / "current.json").read_bytes())


def _published(tmp_path) -> set[str]:
    return {path.name for path in (_site(tmp_path) / "media").iterdir()}


async def test_an_uploaded_file_is_kept_once_and_previewed(client):
    stored = await _store(client, b"png", "image/png", "cover.png")
    again = await _store(client, b"png", "image/png", "cover.png")

    assert again["id"] == stored["id"]
    assert stored["sha256"] == hashlib.sha256(b"png").hexdigest()
    assert (stored["media_type"], stored["size"], stored["filename"]) == (
        "image/png",
        3,
        "cover.png",
    )
    assert stored["projects"] == []
    listed = (await client.get(f"{PORTFOLIO}/assets")).json()
    assert [asset["id"] for asset in listed] == [stored["id"]]
    preview = await client.get(stored["url"])
    assert preview.content == b"png"
    assert preview.headers["content-type"] == "image/png"


async def test_uploads_refuse_other_types_and_files_over_the_limit(client):
    mov = await client.post(
        f"{PORTFOLIO}/uploads", json=_upload(b"mov", "video/quicktime")
    )
    image = await client.post(
        f"{PORTFOLIO}/uploads",
        json={**_upload(b"x", "image/png"), "size": 10 * 1024 * 1024 + 1},
    )
    video = await client.post(
        f"{PORTFOLIO}/uploads",
        json={**_upload(b"x", "video/mp4"), "size": 200 * 1024 * 1024 + 1},
    )

    assert mov.status_code == 422
    assert image.status_code == 422
    assert "Images can be up to 10 MB" in image.text
    assert video.status_code == 422
    assert "Videos can be up to 200 MB" in video.text


async def test_the_local_upload_checks_the_content_against_its_sha256_and_limit(
    client, tmp_path
):
    upload = _upload(b"png", "image/png")
    target = (await client.post(f"{PORTFOLIO}/uploads", json=upload)).json()

    wrong = await client.put(
        target["url"], content=b"other", headers={"Content-Type": "image/png"}
    )
    big = await client.put(
        target["url"],
        content=b"x" * (10 * 1024 * 1024 + 1),
        headers={"Content-Type": "image/png"},
    )
    mov = await client.put(
        target["url"], content=b"png", headers={"Content-Type": "video/quicktime"}
    )

    assert wrong.status_code == 422
    assert big.status_code == 422
    assert mov.status_code == 422
    assert not [path for path in (tmp_path / "private").rglob("*") if path.is_file()]
    missing = await client.post(f"{PORTFOLIO}/assets", json=upload)
    assert missing.status_code == 409


async def test_a_project_shows_an_image_and_a_video_of_the_right_kind(client):
    project = await _project(client)
    role = await _project(client, "Engineer", kind="role")
    image = await _store(client, b"png", "image/png")
    video = await _store(client, b"mp4", "video/mp4")

    assert (await _show(client, project, "image", video)).status_code == 422
    assert (
        await _show(client, project, "video", {"id": str(uuid4())})
    ).status_code == 422
    assert (await _show(client, role, "image", image)).status_code == 404
    assert (await _show(client, project, "image", image)).status_code == 204
    assert (await _show(client, project, "video", video)).status_code == 204

    entry = next(
        e
        for e in (await client.get(f"{PROFILE}/entries")).json()
        if e["id"] == project["id"]
    )
    assert (entry["image_id"], entry["video_id"]) == (image["id"], video["id"])
    assets = (await client.get(f"{PORTFOLIO}/assets")).json()
    assert all(
        a["projects"] == [{"id": project["id"], "title": "Renderverse"}] for a in assets
    )
    saved = await client.put(
        f"{PROFILE}/entries/{project['id']}",
        json={**entry, "title": "Renderverse 2", "image_id": None},
    )
    assert saved.json()["image_id"] == image["id"], "editing an entry keeps its media"

    assert (await _show(client, project, "image", None)).status_code == 204
    entry = (await client.get(f"{PROFILE}/entries")).json()
    assert next(e for e in entry if e["id"] == project["id"])["image_id"] is None


async def test_publishing_copies_the_files_and_names_them_in_current_json(
    client, tmp_path
):
    project = await _project(client)
    image = await _store(client, b"png", "image/png")
    video = await _store(client, b"mp4", "video/mp4")
    await _show(client, project, "image", image)
    await _show(client, project, "video", video)

    draft = (await client.get(f"{PORTFOLIO}/draft")).json()
    await client.post(f"{PORTFOLIO}/releases")

    assert [(c["id"], c["change"]) for c in draft["changes"]][-1] == (
        project["id"],
        "added",
    )
    site = _current(tmp_path)["projects"][0]
    media = f"/sites/{_site(tmp_path).name}/media"
    assert site["image"] == f"{media}/{image['sha256']}.png"
    assert site["video"] == f"{media}/{video['sha256']}.mp4"
    for url, content in ((site["image"], b"png"), (site["video"], b"mp4")):
        assert (tmp_path / "public" / url.removeprefix("/")).read_bytes() == content

    await _show(client, project, "video", None)
    draft = (await client.get(f"{PORTFOLIO}/draft")).json()
    assert [(c["id"], c["change"]) for c in draft["changes"]] == [
        (project["id"], "changed")
    ]


async def test_storage_keeps_the_files_of_the_last_3_live_releases_and_rolling_back_restores(
    client, tmp_path
):
    project = await _project(client)
    covers = [await _store(client, bytes([n]) * 3, "image/jpeg") for n in range(4)]
    releases = []
    for cover in covers:
        await _show(client, project, "image", cover)
        releases.append((await client.post(f"{PORTFOLIO}/releases")).json())

    names = [f"{cover['sha256']}.jpg" for cover in covers]
    assert _published(tmp_path) == {names[1], names[2], names[3]}

    await client.post(f"{PORTFOLIO}/releases/{releases[0]['id']}/live")

    image = _current(tmp_path)["projects"][0]["image"]
    assert image == f"/sites/{_site(tmp_path).name}/media/{names[0]}"
    assert _published(tmp_path) == {names[0], names[3], names[2]}


async def test_a_file_is_deleted_once_no_project_shows_it(client, tmp_path):
    project = await _project(client)
    shown = await _store(client, b"png", "image/png")
    unused = await _store(client, b"jpg", "image/jpeg")
    await _show(client, project, "image", shown)
    await client.post(f"{PORTFOLIO}/releases")

    in_use = await client.delete(f"{PORTFOLIO}/assets/{shown['id']}")
    assert in_use.status_code == 409
    assert "Renderverse shows this file" in in_use.text

    assert (
        await client.delete(f"{PORTFOLIO}/assets/{unused['id']}")
    ).status_code == 204
    assert not list((tmp_path / "private").rglob(unused["sha256"]))

    await _show(client, project, "image", None)
    assert (await client.delete(f"{PORTFOLIO}/assets/{shown['id']}")).status_code == 204
    assert list((tmp_path / "private").rglob(shown["sha256"])), "release 1 shows it"
    assert (await client.get(f"{PORTFOLIO}/assets")).json() == []
    assert (await client.delete(f"{PORTFOLIO}/assets/{shown['id']}")).status_code == 404


async def test_another_user_with_the_same_file_cannot_take_or_delete_yours(
    app, client, tmp_path
):
    async with app.state.session_factory() as session:
        other = User(email="other@example.com", role=Role.ADMIN)
        session.add(other)
        await session.commit()
    project = await _project(client)
    mine = await _store(client, b"png", "image/png")
    await _show(client, project, "image", mine)

    app.dependency_overrides[current_user] = lambda: other
    claimed = await client.post(
        f"{PORTFOLIO}/assets", json=_upload(b"png", "image/png")
    )
    theirs = await _store(client, b"png", "image/png")
    deleted = await client.delete(f"{PORTFOLIO}/assets/{theirs['id']}")
    app.dependency_overrides.clear()

    assert claimed.status_code == 409
    assert deleted.status_code == 204
    first = await client.post(f"{PORTFOLIO}/releases")
    assert first.status_code == 201, first.text
    await _show(client, project, "image", await _store(client, b"jpg", "image/jpeg"))
    assert (await client.post(f"{PORTFOLIO}/releases")).status_code == 201
    back = await client.post(f"{PORTFOLIO}/releases/{first.json()['id']}/live")
    assert back.status_code == 200, back.text
    image = _current(tmp_path)["projects"][0]["image"]
    assert (tmp_path / "public" / image.removeprefix("/")).read_bytes() == b"png"


async def test_each_user_publishes_and_rolls_back_only_their_own_site(
    app, client, tmp_path
):
    async with app.state.session_factory() as session:
        users = [
            User(email="ada@example.com", role=Role.ADMIN),
            User(email="bob@example.com", role=Role.ADMIN),
        ]
        session.add_all(users)
        await session.commit()

    async def publish_twice_then_roll_back(user: User) -> list[str]:
        app.dependency_overrides[current_user] = lambda: user
        project = await _project(client)
        covers, releases = [], []
        for n in (1, 2):
            cover = await _store(client, f"{user.email} {n}".encode(), "image/png")
            covers.append(cover["sha256"])
            await _show(client, project, "image", cover)
            releases.append((await client.post(f"{PORTFOLIO}/releases")).json())
        await client.post(f"{PORTFOLIO}/releases/{releases[0]['id']}/live")
        return covers

    covers = {user.id: await publish_twice_then_roll_back(user) for user in users}
    app.dependency_overrides.clear()

    public = tmp_path / "public"
    assert {
        path.relative_to(public).as_posix()
        for path in public.rglob("*")
        if path.is_file()
    } == {
        key
        for user in users
        for key in (
            f"sites/{user.id}/release/current.json",
            *(f"sites/{user.id}/media/{sha}.png" for sha in covers[user.id]),
        )
    }
    for user in users:
        site = json.loads(
            (public / f"sites/{user.id}/release/current.json").read_text()
        )
        image = site["projects"][0]["image"]
        assert site["number"] == 1
        assert image == f"/sites/{user.id}/media/{covers[user.id][0]}.png"
        assert (public / image.removeprefix("/")).read_bytes() == (
            f"{user.email} 1".encode()
        )


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_a_publish_and_a_roll_back_at_once_leave_one_live_release(
    postgres_app, tmp_path
):
    async with (
        postgres_app.state.session_factory() as other,
        _client(postgres_app) as client,
    ):
        project = await _project(client)
        first = (await client.post(f"{PORTFOLIO}/releases")).json()
        await _show(client, project, "image", await _store(client, b"png", "image/png"))
        second = (await client.post(f"{PORTFOLIO}/releases")).json()
        await _show(
            client, project, "image", await _store(client, b"jpg", "image/jpeg")
        )
        await other.get(PortfolioRelease, UUID(second["id"]), with_for_update=True)

        racing = [
            asyncio.create_task(client.post(f"{PORTFOLIO}/releases")),
            asyncio.create_task(
                client.post(f"{PORTFOLIO}/releases/{first['id']}/live")
            ),
        ]
        async with asyncio.timeout(5):
            while (
                await other.scalar(
                    text("SELECT count(*) FROM pg_locks WHERE NOT granted")
                )
                < 2
            ):
                await asyncio.sleep(0.01)
        await other.commit()
        await asyncio.gather(*racing)
        releases = (await client.get(f"{PORTFOLIO}/releases")).json()

    live = [release for release in releases if release["live"]]
    assert len(live) == 1
    assert _current(tmp_path)["number"] == live[0]["number"]


async def test_every_media_route_needs_a_session(auth_client):
    sha = "0" * 64
    for method, path in (
        ("POST", "uploads"),
        ("PUT", f"uploads/{sha}"),
        ("GET", f"uploads/{sha}"),
        ("POST", "assets"),
        ("GET", "assets"),
        ("DELETE", f"assets/{uuid4()}"),
        ("PUT", f"projects/{uuid4()}/image"),
    ):
        response = await auth_client.request(method, f"{PORTFOLIO}/{path}")
        assert response.status_code == 401, path
