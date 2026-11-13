import asyncio
from collections import Counter
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass
from functools import partial
from typing import Any
from uuid import UUID, uuid4

from fastapi.sse import format_sse_event
from pydantic import BaseModel, ValidationError
from pydantic_core import to_json

from src.clients.ezcareer import (
    Answer,
    Cancelled,
    Completed,
    Decisions,
    EzcareerClient,
    Failed,
    InputRequired,
    ModelCatalog,
    Run,
    RunEvent,
    RunMetadata,
    Started,
    ToolRequest,
)
from src.core.exceptions import NotFound
from src.core.logging import get_logger
from src.core.stores import AgentRunStatus, RunStore

logger = get_logger(__name__)


class ToolError(BaseModel):
    error: str
    """Why ops-api cannot execute the tool, such as No such document"""


@dataclass(frozen=True)
class Tool[R: BaseModel]:
    request: type[R]
    """The model the tool's request parses into"""

    execute: Callable[[UUID, R], Awaitable[BaseModel]]
    """Executes a parsed request for its user and returns the tool result"""


type Tools = Mapping[str, Tool[Any]]
"""A feature's tools, by the name a run asks for"""


type Handle[R] = Callable[[AsyncIterator[RunEvent[R]]], AsyncIterator[BaseModel]]
"""Rewrites a run's events into what the browser gets"""


class ToolExecutor:
    def __init__(self, *features: Tools):
        """Execute every feature's tools; ValueError when two features register the
        same name"""
        names = Counter(name for tools in features for name in tools)
        if repeated := [name for name, count in names.items() if count > 1]:
            raise ValueError(f"Tools registered twice: {repeated}")
        self._tools = {name: tool for tools in features for name, tool in tools.items()}
        """Each tool by the name a paused run asks for it by"""

    async def execute(self, user_id: UUID, request: ToolRequest) -> BaseModel:
        """The tool result a paused run resumes with, for the user; ToolError for a
        tool ops-api lacks or a malformed request"""
        match self._tools.get(request.execute_tool):
            case None:
                result = ToolError(error=f"Ops has no {request.execute_tool} tool")
                outcome = "unknown"
            case tool:
                try:
                    parsed = tool.request.model_validate(request.model_dump())
                except ValidationError as error:
                    result = ToolError(error=str(error))
                    outcome = "malformed"
                else:
                    result = await tool.execute(user_id, parsed)
                    outcome = "refused" if isinstance(result, ToolError) else "executed"
        logger.info(
            "tool_execution",
            tool=request.execute_tool,
            user_id=str(user_id),
            outcome=outcome,
        )
        return result


class AgentRunner:
    def __init__(
        self,
        ezcareer: EzcareerClient,
        tools: ToolExecutor,
        store: RunStore,
        retry_ms: int,
    ):
        """Run the harness's agents and workflows for a user, executing the tools a
        run pauses on, and keep each streamed run's events so any process can
        stream them"""
        self._ezcareer = ezcareer
        """The harness"""

        self._tools = tools
        """What executes the tools a run pauses on"""

        self._store = store
        """Where each streamed run's events are kept"""

        self._retry_ms = retry_ms
        """The retry hint each stream starts with"""

        self._tasks: set[asyncio.Task[None]] = set()
        """Every run still writing, kept so none is garbage collected mid-run"""

    async def models(self) -> ModelCatalog:
        """The models the harness offers, by provider"""
        return await self._ezcareer.models()

    async def run[R](
        self,
        user_id: UUID,
        executable: str,
        reply: type[R],
        *,
        data: BaseModel,
        metadata: RunMetadata | None,
    ) -> Run[R]:
        """Run an agent or workflow on the data to its end on a thread of its own,
        executing the tools it pauses on; how it ended"""
        return await self._ezcareer.send(
            executable,
            reply,
            user_id=user_id,
            context_id=f"{user_id}:{uuid4()}",
            data=data,
            metadata=metadata,
            execute_tool=partial(self._tools.execute, user_id),
        )

    async def _write(self, run_id: str, events: AsyncIterator[BaseModel]) -> None:
        """Write each of the run's events to the store, then mark it finished with how
        its last event ended it, failed without one, or cancelled when stopped"""
        seq = 0
        status = AgentRunStatus.FAILED
        task_id = None
        try:
            async for event in events:
                match event:
                    case Started():
                        task_id = event.task_id
                    case Completed() | InputRequired() | Failed() | Cancelled():
                        status = AgentRunStatus(event.status)
                seq += 1
                await self._store.append(run_id, seq, event.model_dump(mode="json"))
        except asyncio.CancelledError:
            status = AgentRunStatus.CANCELLED
            raise
        finally:
            await self._store.finish(run_id, status, task_id)

    async def _read(self, run_id: str, after: int) -> AsyncIterator[str]:
        """The run's events after the first `after` as server-sent events with run:seq
        ids, then each new one until it ends"""
        seq = after
        async for data in self._store.read(run_id, after):
            seq += 1
            yield format_sse_event(
                data_str=to_json(data).decode(),
                id=f"{run_id}:{seq}",
                retry=self._retry_ms if seq == 1 else None,
            ).decode()

    async def _start(
        self,
        user_id: UUID,
        thread_id: str,
        executable: str,
        events: AsyncIterator[BaseModel],
    ) -> AsyncIterator[str]:
        """Write the events in the background as a new run on thread_id, the A2A
        context_id, and stream it from the start; Conflict while thread_id's last run
        is still going"""
        run_id = await self._store.create(user_id, thread_id, executable)
        task = asyncio.create_task(self._write(run_id, events))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return self._read(run_id, 0)

    async def start[R](
        self,
        user_id: UUID,
        thread_id: str,
        executable: str,
        reply: type[R],
        *,
        data: BaseModel,
        metadata: RunMetadata | None,
        text: str = "",
        handle: Handle[R] | None = None,
    ) -> AsyncIterator[str]:
        """Start a run of the agent or workflow on the thread, executing the tools
        it pauses on, and stream its events, rewritten by handle when given"""
        events = self._ezcareer.stream(
            executable,
            reply,
            user_id=user_id,
            context_id=thread_id,
            text=text,
            data=data,
            metadata=metadata,
            execute_tool=partial(self._tools.execute, user_id),
        )
        return await self._start(
            user_id, thread_id, executable, handle(events) if handle else events
        )

    def answered[R](
        self,
        user_id: UUID,
        thread_id: str,
        executable: str,
        reply: type[R],
        *,
        task_id: str,
        answer: Answer | Decisions,
        metadata: RunMetadata | None,
    ) -> AsyncIterator[RunEvent[R]]:
        """The rest of a paused task's events once it has the user's answer or
        decisions, its tools executed, without keeping them"""
        return self._ezcareer.stream_resume(
            executable,
            reply,
            user_id=user_id,
            context_id=thread_id,
            task_id=task_id,
            answer=answer,
            metadata=metadata,
            execute_tool=partial(self._tools.execute, user_id),
        )

    async def answer[R](
        self,
        user_id: UUID,
        thread_id: str,
        executable: str,
        reply: type[R],
        *,
        task_id: str,
        answer: Answer | Decisions,
        metadata: RunMetadata | None,
        handle: Handle[R] | None = None,
    ) -> AsyncIterator[str]:
        """Answer the widget or review a paused task of the thread asked and stream
        the rest of its run as start does"""
        events = self.answered(
            user_id,
            thread_id,
            executable,
            reply,
            task_id=task_id,
            answer=answer,
            metadata=metadata,
        )
        return await self._start(
            user_id, thread_id, executable, handle(events) if handle else events
        )

    async def resume(
        self, thread_id: str, last_event_id: str | None
    ) -> AsyncIterator[str]:
        """Stream thread_id's run after the Last-Event-ID the client last saw; NotFound
        when there is none to resume or the id is another run's"""
        run_id, count = await self._store.latest(thread_id)
        if not last_event_id:
            return self._read(run_id, 0)
        seen_run_id, _, seq = last_event_id.partition(":")
        if seen_run_id != run_id or not seq.isdigit():
            raise NotFound("There is no reply to resume")
        return self._read(run_id, min(int(seq), count))

    async def cancel(self, executable: str, task_id: str, thread_id: str) -> None:
        """Stop the thread's running task"""
        await self._ezcareer.cancel(executable, task_id, thread_id)

    async def aclose(self) -> None:
        """Cancel every run still writing and wait until each is marked finished"""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)


__all__ = ["AgentRunner", "Handle", "Tool", "ToolError", "ToolExecutor", "Tools"]
