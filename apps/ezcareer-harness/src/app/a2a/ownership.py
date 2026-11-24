import asyncio
from collections.abc import Awaitable, Callable, Mapping
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from a2a.helpers import new_text_part
from a2a.server.cluster import StoredTask, VersionedTaskStore
from a2a.server.context import ServerCallContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import TaskStore
from a2a.types import (
    ListTasksRequest,
    Message,
    Role,
    SendMessageConfiguration,
    SendMessageRequest,
    TaskState,
)
from google.protobuf.json_format import MessageToDict

from src.core.config import TaskSettings
from src.infrastructure import get_logger
from src.infrastructure.persistence import TaskOwners

logger = get_logger(__name__)


async def _every(seconds: float, step: Callable[[], Awaitable[None]]) -> None:
    """Runs step every seconds, logging a failed step and carrying on"""
    while True:
        await asyncio.sleep(seconds)
        try:
            await step()
        except Exception:
            logger.exception("task ownership step failed")


class Ownership:
    def __init__(self, owners: TaskOwners, settings: TaskSettings) -> None:
        """Owns the tasks this process runs and takes over those of dead processes"""
        self.owners = owners
        """Which process owns each running task"""

        self.settings = settings
        """How often to beat and sweep, and when an owner counts as dead"""

        self.runs: dict[str, asyncio.Task] = {}
        """This process's run of each task it owns"""

    async def claim(self, task_id: str) -> None:
        """Owns the task and keeps its run, the current asyncio task, to cancel when
        another process takes the task over"""
        await self.owners.claim(task_id)
        if run := asyncio.current_task():
            self.runs[task_id] = run

    async def drop(self, task_id: str) -> None:
        """Gives up the task once its run stopped: completed, failed, cancelled or
        paused"""
        self.runs.pop(task_id, None)
        await self.owners.drop(task_id)

    async def confirm(self, task_id: str) -> None:
        """Cancels the current run, before it ends its task, when another process
        has taken the task over"""
        if not await self.owners.owns(task_id):
            logger.warning("task taken over", task_id=task_id)
            self.runs.pop(task_id, None)
            raise asyncio.CancelledError

    def thread(
        self, thread_id: str, wait: bool = True
    ) -> AbstractAsyncContextManager[bool]:
        """Holds exclusive use of the thread while open, waiting for an earlier run on
        it to stop unless told not to; whether it got it in time"""
        return self.owners.thread(
            thread_id, self.settings.thread_wait_seconds if wait else 0
        )

    async def heartbeat(self, task_store: TaskStore | VersionedTaskStore) -> None:
        """Marks this process's tasks alive, cancels runs taken over or cancelled
        elsewhere, and drops tasks whose run stopped without dropping them"""
        runs = dict(self.runs)
        alive = await self.owners.beat()
        for task_id, run in runs.items():
            if self.runs.get(task_id) is not run:
                continue
            if task_id not in alive:
                logger.warning("task taken over", task_id=task_id)
                del self.runs[task_id]
                run.cancel()
            elif run.done():
                await self.drop(task_id)
            else:
                stored = await task_store.get(task_id, ServerCallContext())
                task = stored.task if isinstance(stored, StoredTask) else stored
                if task and task.status.state == TaskState.TASK_STATE_CANCELED:
                    logger.warning("task cancelled elsewhere", task_id=task_id)
                    run.cancel()

    async def sweep(
        self,
        handlers: Mapping[str, DefaultRequestHandler],
        task_store: TaskStore | VersionedTaskStore,
    ) -> None:
        """Takes over working tasks whose owner died or never existed, and resumes each
        from its thread's checkpoint, or fails it when too old or a workflow's"""
        context = ServerCallContext()
        dead_after = self.settings.dead_after_seconds
        taken = await self.owners.take_stale(dead_after)
        request = ListTasksRequest(status=TaskState.TASK_STATE_WORKING)
        quiet_since = datetime.now(UTC) - timedelta(seconds=dead_after)
        while True:
            page = await task_store.list(request, context)
            for task in page.tasks:
                if task.status.timestamp.ToDatetime(
                    UTC
                ) < quiet_since and await self.owners.take_unowned(task.id, dead_after):
                    taken.append(task.id)
            if not page.next_page_token:
                break
            request.page_token = page.next_page_token
        cutoff = datetime.now(UTC) - timedelta(
            seconds=self.settings.resume_window_seconds
        )
        for task_id in taken:
            stored = await task_store.get(task_id, context)
            task = stored.task if isinstance(stored, StoredTask) else stored
            setup = MessageToDict(task.metadata) if task else {}
            handler = handlers.get(setup.get("executable", ""))
            if (
                task is None
                or task.status.state != TaskState.TASK_STATE_WORKING
                or handler is None
            ):
                await self.owners.drop(task_id)
                continue
            message = Message(
                message_id=uuid4().hex,
                role=Role.ROLE_USER,
                task_id=task.id,
                context_id=task.context_id,
                parts=[new_text_part("restart")],
            )
            message.metadata.update(
                {
                    "restart": "resume"
                    if handler.agent_executor.executable.kind == "agent"
                    and task.status.timestamp.ToDatetime(UTC) >= cutoff
                    else "fail"
                }
            )
            send = SendMessageRequest(
                message=message,
                configuration=SendMessageConfiguration(return_immediately=True),
            )
            send.metadata.update(setup.get("run", {}))
            try:
                await handler.on_message_send(send, context)
            except Exception:
                logger.exception("task did not restart", task_id=task_id)
                await self.owners.drop(task_id)

    async def keep(
        self,
        handlers: Mapping[str, DefaultRequestHandler],
        task_store: TaskStore | VersionedTaskStore,
    ) -> None:
        """Beats and sweeps on their intervals until cancelled"""
        await asyncio.gather(
            _every(self.settings.heartbeat_seconds, lambda: self.heartbeat(task_store)),
            _every(
                self.settings.sweep_seconds, lambda: self.sweep(handlers, task_store)
            ),
        )
