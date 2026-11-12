import asyncio
import signal
from contextlib import suppress
from datetime import timedelta
from uuid import UUID

from src.app.container import Container
from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger
from src.db import models  # noqa: F401
from src.features.imports.processing import (
    claim_import,
    fail_lapsed,
    heartbeat,
    process_import,
    release_import,
)

logger = get_logger(__name__)


async def _process(
    container: Container, import_id: UUID, claim_token: UUID, stop: asyncio.Event
) -> None:
    """Process the claimed import, extending its lease until it ends; stop it once
    the claim is lost, or when stop is set, releasing the claim"""
    settings = container.settings().imports
    factory = container.session_factory()
    task = asyncio.create_task(process_import(import_id, claim_token, container))
    stopping = asyncio.create_task(stop.wait())
    while True:
        await asyncio.wait(
            {task, stopping},
            timeout=settings.heartbeat_seconds,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if task.done() or stop.is_set():
            break
        try:
            async with factory() as session, session.begin():
                held = await heartbeat(
                    session,
                    import_id,
                    claim_token,
                    timedelta(seconds=settings.lease_seconds),
                )
        except Exception:
            logger.exception("import_heartbeat_failed", import_id=str(import_id))
            continue
        if not held:
            task.cancel()
    stopping.cancel()
    if stop.is_set():
        task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        if not stop.is_set():
            logger.info("import_claim_lost", import_id=str(import_id))
            return
        async with factory() as session, session.begin():
            released = await release_import(session, import_id, claim_token)
        if released:
            logger.info("import_released", import_id=str(import_id))


async def run(container: Container, stop: asyncio.Event) -> None:
    """Claim and process imports, one at a time, until stop is set"""
    settings = container.settings().imports
    factory = container.session_factory()
    while not stop.is_set():
        try:
            async with factory() as session, session.begin():
                lapsed = await fail_lapsed(session)
                claimed = await claim_import(
                    session, timedelta(seconds=settings.lease_seconds)
                )
            if lapsed:
                logger.warning("imports_lapsed", count=lapsed)
            if claimed is not None:
                logger.info(
                    "import_claimed",
                    import_id=str(claimed.id),
                    attempt=claimed.attempts,
                )
                await _process(container, claimed.id, claimed.claim_token, stop)
                continue
        except Exception:
            logger.exception("worker_iteration_failed")
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), settings.poll_seconds)


async def main() -> None:
    """Run the worker until SIGINT or SIGTERM"""
    settings = get_settings()
    configure_logging(settings)
    container = Container()
    stop = asyncio.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(signum, stop.set)
    logger.info("worker_started")
    try:
        await run(container, stop)
    finally:
        await container.runner().aclose()
        await container.artifact().aclose()
        await container.ezcareer().aclose()
        await container.store().aclose()
        await container.google().aclose()
        await container.engine().dispose()
    logger.info("worker_stopped")


if __name__ == "__main__":
    asyncio.run(main())
