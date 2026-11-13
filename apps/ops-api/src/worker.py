import asyncio
import signal
from collections.abc import Awaitable, Callable
from contextlib import suppress
from datetime import timedelta
from uuid import UUID

from src.app.container import Container
from src.core.config import get_settings
from src.core.logging import configure_logging, get_logger
from src.db import models  # noqa: F401
from src.db.queue import Claimable, Queue, claim, fail_lapsed, heartbeat, release
from src.features.imports.processing import IMPORTS, process_import
from src.features.jobs.processing import (
    JOB_RUNS,
    enqueue_scheduled_runs,
    process_job_run,
)

logger = get_logger(__name__)

QUEUES = ((IMPORTS, process_import), (JOB_RUNS, process_job_run))
"""Each queue the worker claims from, with what processes a claimed row"""


async def _process[R: Claimable](
    container: Container,
    queue: Queue[R],
    process: Callable[[UUID, UUID, Container], Awaitable[None]],
    row_id: UUID,
    claim_token: UUID,
    stop: asyncio.Event,
) -> None:
    """Process the claimed row, extending its lease until it ends; stop it once the
    claim is lost, or when stop is set, releasing the claim"""
    settings = container.settings().worker
    factory = container.session_factory()
    table = queue.model.__tablename__
    task = asyncio.create_task(process(row_id, claim_token, container))
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
                    queue,
                    row_id,
                    claim_token,
                    timedelta(seconds=settings.lease_seconds),
                )
        except Exception:
            logger.exception("heartbeat_failed", table=table, id=str(row_id))
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
            logger.info("claim_lost", table=table, id=str(row_id))
            return
        async with factory() as session, session.begin():
            released = await release(session, queue, row_id, claim_token)
        if released:
            logger.info("released", table=table, id=str(row_id))


async def _work(container: Container, stop: asyncio.Event, first: int) -> bool:
    """Fail lapsed rows and process the first row due on any queue, trying the
    queues from the one at first; whether one was"""
    settings = container.settings().worker
    factory = container.session_factory()
    for queue, process in QUEUES[first:] + QUEUES[:first]:
        table = queue.model.__tablename__
        async with factory() as session, session.begin():
            lapsed = await fail_lapsed(session, queue)
            claimed = await claim(
                session, queue, timedelta(seconds=settings.lease_seconds)
            )
        if lapsed:
            logger.warning("lapsed", table=table, count=lapsed)
        if claimed is not None:
            logger.info(
                "claimed", table=table, id=str(claimed.id), attempt=claimed.attempts
            )
            await _process(
                container, queue, process, claimed.id, claimed.claim_token, stop
            )
            return True
    return False


async def run(container: Container, stop: asyncio.Event) -> None:
    """Claim and process rows, one at a time and each queue first in turn, until
    stop is set"""
    settings = container.settings().worker
    turn = 0
    while not stop.is_set():
        try:
            worked = await _work(container, stop, turn)
        except Exception:
            logger.exception("worker_iteration_failed")
            worked = False
        turn = (turn + 1) % len(QUEUES)
        if not worked:
            with suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), settings.poll_seconds)


async def tick(container: Container, stop: asyncio.Event) -> None:
    """Queue the scheduled job runs due, every tick_seconds until stop is set"""
    settings = container.settings().worker
    factory = container.session_factory()
    while not stop.is_set():
        try:
            async with factory() as session, session.begin():
                queued = await enqueue_scheduled_runs(session)
            if queued:
                logger.info("job_runs_scheduled", count=queued)
        except Exception:
            logger.exception("tick_failed")
        with suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), settings.tick_seconds)


async def main() -> None:
    """Run the worker's claim loop and its tick until SIGINT or SIGTERM"""
    settings = get_settings()
    configure_logging(settings)
    container = Container()
    stop = asyncio.Event()
    for signum in (signal.SIGINT, signal.SIGTERM):
        asyncio.get_running_loop().add_signal_handler(signum, stop.set)
    logger.info("worker_started")
    try:
        await asyncio.gather(run(container, stop), tick(container, stop))
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
