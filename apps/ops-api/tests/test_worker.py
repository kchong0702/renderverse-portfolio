import asyncio
from uuid import UUID

from dependency_injector import providers

from src import worker
from src.features.imports.models import Import
from src.features.imports.processing import claim_import
from tests.conftest import PREFIX, work
from tests.features.imports.test_processing import _imported, _listed, _upload


def _quick(app) -> None:
    """Make the worker poll and heartbeat every few milliseconds"""
    settings = app.state.container.settings()
    app.state.container.settings.override(
        providers.Object(
            settings.model_copy(
                update={
                    "imports": settings.imports.model_copy(
                        update={"poll_seconds": 0.01, "heartbeat_seconds": 0.02}
                    )
                }
            )
        )
    )


async def test_the_worker_goes_on_after_an_iteration_fails(
    app, client, harness, monkeypatch
):
    _quick(app)
    uploaded = await _upload(client)
    harness.outcomes = [_imported()]
    claims = []

    async def flaky(session, lease):
        claims.append(len(claims))
        if len(claims) == 1:
            raise RuntimeError("the database went away")
        return await claim_import(session, lease)

    monkeypatch.setattr(worker, "claim_import", flaky)
    stop = asyncio.Event()

    async def until_done() -> None:
        while (await _listed(client, uploaded["id"]))["status"] != "done":
            await asyncio.sleep(0.02)
        stop.set()

    await asyncio.wait_for(
        asyncio.gather(worker.run(app.state.container, stop), until_done()), 10
    )

    assert len(claims) >= 2
    assert (await _listed(client, uploaded["id"]))["status"] == "done"


async def test_stopping_the_worker_releases_the_import_it_was_reading(
    app, client, harness, storage, monkeypatch
):
    _quick(app)
    uploaded = await _upload(client)
    stop = asyncio.Event()

    async def hang(key: str) -> None:
        stop.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(storage, "read_private", hang)

    await asyncio.wait_for(worker.run(app.state.container, stop), 10)

    async with app.state.session_factory() as session:
        row = await session.get_one(Import, UUID(uploaded["id"]))
        assert (row.status.value, row.attempts, row.claim_token) == ("queued", 0, None)
    assert harness.received == []
    monkeypatch.undo()
    harness.outcomes = [_imported()]
    await work(app)
    done = await _listed(client, uploaded["id"])
    assert done["status"] == "done"
    assert (await client.get(f"{PREFIX}/imports/active")).json() == []
