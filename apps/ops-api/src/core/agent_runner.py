import asyncio
from collections import Counter
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import partial
from typing import Any
from uuid import UUID, uuid4

from fastapi.sse import format_sse_event
from pydantic import BaseModel, JsonValue, RootModel, ValidationError
from pydantic_core import to_json
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_delay,
    wait_exponential_jitter,
)

from src.clients.ezcareer import (
    AgentRunFailed,
    Answer,
    Cancelled,
    Completed,
    Decisions,
    EzcareerClient,
    Failed,
    HarnessUnreachable,
    InputRequired,
    MessageMetadata,
    ModelCatalog,
    Reconnected,
    Reconnecting,
    RunEvent,
    RunMetadata,
    Started,
    SummaryUpdate,
    ThreadSummary,
    ToolRequest,
    ToolsRequested,
)
from src.core.config import EzcareerSettings
from src.core.exceptions import (
    Conflict,
    NotFound,
    ServiceException,
    ServiceUnavailable,
)
from src.core.logging import get_logger
from src.core.stores import (
    AgentRunStatus,
    AgentToolResult,
    RunLost,
    RunRecord,
    RunStore,
)
from src.db.base import utcnow

logger = get_logger(__name__)


class GaveUp(Failed):
    pass


class ToolError(BaseModel):
    error: str
    """Why ops-api cannot execute the tool, such as No such document"""


@dataclass(frozen=True)
class Tool[R: BaseModel]:
    request: type[R]
    """The model the tool's request parses into"""

    execute: Callable[[UUID, R], Awaitable[BaseModel]]
    """Executes a parsed request for its user and returns the tool result"""


@dataclass(frozen=True)
class WriteTool[R: BaseModel]:
    request: type[R]
    """The model the tool's request parses into"""

    execute: Callable[[AsyncSession, UUID, R], Awaitable[BaseModel]]
    """Makes the write on the session, which commits it with the result kept under
    the request's interrupt; a ToolError rolls it back"""


type Tools = Mapping[str, Tool[Any] | WriteTool[Any]]
"""A feature's tools, by the name a run asks for"""


class ToolExecutor:
    def __init__(
        self,
        features: Sequence[Tools],
        factory: async_sessionmaker[AsyncSession],
    ):
        """Execute every feature's tools, each write once per interrupt; ValueError
        when two features register the same name"""
        names = Counter(name for tools in features for name in tools)
        if repeated := [name for name, count in names.items() if count > 1]:
            raise ValueError(f"Tools registered twice: {repeated}")
        self._tools = {name: tool for tools in features for name, tool in tools.items()}
        """Each tool by the name a paused run asks for it by"""

        self._factory = factory
        """Sessions a write and its kept result commit on"""

    async def _write(
        self,
        tool: WriteTool[Any],
        user_id: UUID,
        task_id: str,
        interrupt_id: str,
        request: ToolRequest,
        parsed: BaseModel,
    ) -> tuple[BaseModel, str]:
        """The write tool's result kept for the interrupt, or the result of making the
        write and keeping it in the same transaction; with how it went"""
        async with self._factory() as session:
            if kept := await session.get(AgentToolResult, interrupt_id):
                return RootModel[dict[str, JsonValue]](kept.result), "repeated"
            result = await tool.execute(session, user_id, parsed)
            if isinstance(result, ToolError):
                await session.rollback()
                return result, "refused"
            session.add(
                AgentToolResult(
                    user_id=user_id,
                    interrupt_id=interrupt_id,
                    task_id=task_id,
                    tool=request.execute_tool,
                    result=result.model_dump(mode="json", by_alias=True),
                )
            )
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                kept = await session.get(AgentToolResult, interrupt_id)
                if kept is None:
                    raise
                return RootModel[dict[str, JsonValue]](kept.result), "repeated"
        return result, "executed"

    async def execute(
        self, user_id: UUID, task_id: str, interrupt_id: str, request: ToolRequest
    ) -> BaseModel:
        """The tool result a paused task resumes with; ToolError for an unknown tool, a
        malformed request or a tool that raised, and a write's first result again"""
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
                    try:
                        if isinstance(tool, WriteTool):
                            result, outcome = await self._write(
                                tool, user_id, task_id, interrupt_id, request, parsed
                            )
                        else:
                            result = await tool.execute(user_id, parsed)
                            outcome = (
                                "refused"
                                if isinstance(result, ToolError)
                                else "executed"
                            )
                    except Exception:
                        logger.exception(
                            "tool_failed",
                            tool=request.execute_tool,
                            user_id=str(user_id),
                            task_id=task_id,
                        )
                        result = ToolError(
                            error=f"Ops failed to execute {request.execute_tool}"
                        )
                        outcome = "failed"
        logger.info(
            "tool_execution",
            tool=request.execute_tool,
            user_id=str(user_id),
            outcome=outcome,
        )
        return result

    async def forget(self, task_id: str) -> None:
        """Drop the write results kept for the task, once its run has ended"""
        async with self._factory() as session, session.begin():
            await session.execute(
                delete(AgentToolResult).where(AgentToolResult.task_id == task_id)
            )


type Send = Callable[[], Awaitable[str | Failed]]
"""Sends a run's next message to the harness and returns its task's id, or why the
harness refused it"""


type Handle = Callable[
    [Turn, str, AsyncIterator[RunEvent[str]]], AsyncIterator[BaseModel]
]
"""Rewrites the events of a turn's run, given its id, into what the browser gets"""


@dataclass(frozen=True)
class Turn:
    user_id: UUID
    """Who the turn is for"""

    thread_id: str
    """The thread the turn is on, the A2A context_id"""

    agent: str
    """The served agent the thread sends its turns to"""

    metadata: RunMetadata | None
    """The model each message to the harness carries"""

    handle: Handle
    """Rewrites the run's events into what the browser gets"""


class AgentRunner:
    def __init__(
        self,
        ezcareer: EzcareerClient,
        tools: ToolExecutor,
        store: RunStore,
        settings: EzcareerSettings,
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

        self._settings = settings
        """The retry hint each stream starts with, how a run reaches the harness again,
        and how often to heartbeat and sweep"""

        self._writing: dict[str, asyncio.Task[None]] = {}
        """Each run this process writes, by run id, until it starts finishing"""

        self._finishing: set[asyncio.Task[None]] = set()
        """Writers saving their run's end, which shutdown waits for"""

        self._loops: list[asyncio.Task[None]] = []
        """The heartbeat and sweep loops, once recover started them"""

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
    ) -> R:
        """The reply of a run to its end on its own thread, running the tools it pauses
        on; ServiceUnavailable when it asks for input, AgentRunFailed when it fails"""
        asked: set[str] = set()

        async def execute(
            task_id: str, interrupt_id: str, request: ToolRequest
        ) -> BaseModel:
            """Execute the tool for the user, noting its task to forget after"""
            asked.add(task_id)
            return await self._tools.execute(user_id, task_id, interrupt_id, request)

        try:
            outcome = await self._ezcareer.send(
                executable,
                reply,
                user_id=user_id,
                context_id=f"{user_id}:{uuid4()}",
                data=data,
                metadata=metadata,
                execute_tool=execute,
            )
        finally:
            for task_id in asked:
                await self._tools.forget(task_id)
        match outcome:
            case Completed(reply=result):
                return result
            case InputRequired():
                raise ServiceUnavailable(
                    f"{executable} asked for input ops cannot give"
                )
            case Failed(reason=reason, next=next_screen):
                raise AgentRunFailed(reason, next_screen)

    async def _results(self, turn: Turn, requested: ToolsRequested) -> Send:
        """Execute together the tools a paused task asks for, and return the send of
        their results"""
        results = await asyncio.gather(
            *(
                self._tools.execute(
                    turn.user_id, requested.task_id, interrupt_id, request
                )
                for interrupt_id, request in requested.requests
            )
        )
        return partial(
            self._ezcareer.results,
            turn.agent,
            context_id=turn.thread_id,
            task_id=requested.task_id,
            results=[
                (interrupt_id, result)
                for (interrupt_id, _), result in zip(
                    requested.requests, results, strict=True
                )
            ],
            metadata=turn.metadata,
        )

    async def _events(
        self,
        turn: Turn,
        run_id: str,
        step: Send | str | None,
        since: datetime | None,
        task_id: str | None = None,
    ) -> AsyncIterator[RunEvent[str]]:
        """The run's events: send step, follow the task, answer the tools it asks for,
        and reach the harness again when lost (step None), failing after a while"""
        announced = task_id if step is None else None
        while True:
            if step is None:
                state = None
                delay = 0.0

                async def wait(seconds: float) -> None:
                    """Keep the backoff for the next try to announce and sleep"""
                    nonlocal delay
                    delay = seconds

                try:
                    async for attempt in AsyncRetrying(
                        wait=wait_exponential_jitter(
                            initial=self._settings.reconnect_initial_wait_seconds,
                            max=self._settings.reconnect_max_wait_seconds,
                        ),
                        stop=stop_after_delay(self._settings.reconnect_seconds),
                        retry=retry_if_exception_type(HarnessUnreachable),
                        sleep=wait,
                        reraise=True,
                    ):
                        yield Reconnecting(
                            attempt=attempt.retry_state.attempt_number,
                            retry_at=utcnow() + timedelta(seconds=delay),
                        )
                        await asyncio.sleep(delay)
                        with attempt:
                            state = await self._ezcareer.state(
                                turn.agent, task_id, turn.thread_id, since
                            )
                except HarnessUnreachable:
                    logger.warning("harness_given_up", run_id=run_id)
                    yield GaveUp(
                        reason="The assistant stopped responding."
                        " Send your message again."
                    )
                    if task_id:
                        with suppress(ServiceException):
                            await self._ezcareer.cancel(
                                turn.agent, task_id, turn.thread_id
                            )
                    return
                yield Reconnected()
                if state is None:
                    yield Failed(
                        reason="The assistant lost this reply. Send your message again."
                    )
                    return
                task_id = state.task_id
                match state.events:
                    case []:
                        step = task_id
                    case [ToolsRequested() as requested]:
                        step = await self._results(turn, requested)
                    case events:
                        for event in events:
                            yield event
                        return
            try:
                if not isinstance(step, str):
                    sent = await step()
                    if isinstance(sent, Failed):
                        yield sent
                        return
                    step = sent
                task_id = step
                if task_id != announced:
                    announced = task_id
                    yield Started(task_id=task_id)
                requested = None
                async for event in self._ezcareer.follow(
                    turn.agent, turn.user_id, turn.thread_id, task_id
                ):
                    if isinstance(event, ToolsRequested):
                        requested = event
                    else:
                        yield event
                if requested is None:
                    return
                step = await self._results(turn, requested)
            except HarnessUnreachable as error:
                logger.warning("harness_lost", run_id=run_id, reason=str(error))
                step = None

    async def _write(
        self,
        run_id: str,
        seq: int,
        task_id: str | None,
        events: AsyncIterator[BaseModel],
    ) -> None:
        """Keep the run's events after seq and finish it as its last event left it; a
        shutdown or another process taking the run over leaves it running"""
        status = AgentRunStatus.FAILED
        stopped = False
        try:
            last = None
            async for event in events:
                if isinstance(event, Started):
                    task_id = event.task_id
                    await self._store.set_task(run_id, task_id)
                seq += 1
                await self._store.append(run_id, seq, event.model_dump(mode="json"))
                last = event
            match last:
                case Completed():
                    status = AgentRunStatus.COMPLETED
                case Cancelled():
                    status = AgentRunStatus.CANCELLED
                case GaveUp():
                    status = AgentRunStatus.ABANDONED
                case Failed() | None:
                    status = AgentRunStatus.FAILED
                case _:
                    status = AgentRunStatus.INPUT_REQUIRED
        except asyncio.CancelledError:
            stopped = True
            raise
        except RunLost:
            stopped = True
            logger.warning("run_lost", run_id=run_id)
        finally:
            if not stopped and (finishing := asyncio.current_task()):
                self._writing.pop(run_id, None)
                self._finishing.add(finishing)
                try:
                    with suppress(RunLost):
                        await self._store.finish(run_id, status, task_id)
                        if task_id:
                            await self._tools.forget(task_id)
                finally:
                    self._finishing.discard(finishing)

    def _spawn(
        self,
        run_id: str,
        seq: int,
        task_id: str | None,
        events: AsyncIterator[BaseModel],
    ) -> None:
        """Write the run's events in the background, stopping a stale writer of it"""
        if stale := self._writing.get(run_id):
            stale.cancel()
        task = asyncio.create_task(self._write(run_id, seq, task_id, events))
        self._writing[run_id] = task

        def written(done: asyncio.Task[None]) -> None:
            """Forget the writer once it ends, unless a newer one replaced it"""
            if self._writing.get(run_id) is done:
                del self._writing[run_id]

        task.add_done_callback(written)

    async def _read(self, run_id: str, after: int) -> AsyncIterator[str]:
        """The run's events after the first `after` as server-sent events with run:seq
        ids, then each new one until it ends"""
        seq = after
        async for data in self._store.read(run_id, after):
            seq += 1
            yield format_sse_event(
                data_str=to_json(data).decode(),
                id=f"{run_id}:{seq}",
                retry=self._settings.stream_retry_ms if seq == 1 else None,
            ).decode()

    async def _settle(self, turn: Turn) -> None:
        """Keep the reply of the thread's last task ops-api gave up following, found
        by its run's start if never named, or stop it; Conflict when it won't stop"""
        if (abandoned := await self._store.abandoned(turn.thread_id)) is None:
            return
        run_id, task_id, started_at = abandoned
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._settings.stop_wait_seconds
        cancelled = False
        while True:
            try:
                state = await self._ezcareer.state(
                    turn.agent, task_id, turn.thread_id, started_at
                )
            except HarnessUnreachable as error:
                raise ServiceUnavailable(
                    "ezcareer-harness did not say how the last reply ended;"
                    " try again later"
                ) from error
            if state is None:
                return
            task_id = state.task_id
            events = [e for e in state.events if not isinstance(e, ToolsRequested)]
            match events[-1:]:
                case [Failed() | Cancelled()]:
                    return
                case [Completed()]:
                    break
            if loop.time() >= deadline:
                raise Conflict("The last reply is still stopping; try again shortly")
            if cancelled:
                await asyncio.sleep(self._settings.reconnect_initial_wait_seconds)
            else:
                await self._ezcareer.cancel(turn.agent, task_id, turn.thread_id)
                cancelled = True

        async def ended() -> AsyncIterator[RunEvent[str]]:
            """The events the finished task ended with"""
            for event in events:
                yield event

        async for _ in turn.handle(turn, run_id, ended()):
            pass

    async def start(
        self,
        turn: Turn,
        *,
        message_id: str,
        text: str,
        sent: MessageMetadata,
        data: BaseModel,
        prepare: Callable[[], Awaitable[None]],
    ) -> AsyncIterator[str]:
        """Settle the task the thread's last run gave up on, prepare, send the message
        on a new run and stream its events; Conflict while the thread's run goes on"""
        await self._settle(turn)
        run_id = await self._store.create(turn.user_id, turn.thread_id, turn.agent)
        since = utcnow()
        try:
            await prepare()
        except BaseException:
            await self._store.finish(run_id, AgentRunStatus.FAILED, None)
            raise
        send = partial(
            self._ezcareer.start,
            turn.agent,
            context_id=turn.thread_id,
            message_id=message_id,
            text=text,
            sent=sent,
            data=data,
            metadata=turn.metadata,
        )
        self._spawn(
            run_id,
            0,
            None,
            turn.handle(turn, run_id, self._events(turn, run_id, send, since)),
        )
        return self._read(run_id, 0)

    def answered(
        self, turn: Turn, run_id: str, task_id: str, answer: Answer | Decisions
    ) -> AsyncIterator[RunEvent[str]]:
        """The rest of a paused task's events once it has the user's answer or
        decisions, as part of the run run_id, its tools executed"""
        return self._events(
            turn,
            run_id,
            partial(
                self._ezcareer.answer,
                turn.agent,
                context_id=turn.thread_id,
                task_id=task_id,
                answer=answer,
                metadata=turn.metadata,
            ),
            None,
            task_id,
        )

    async def answer(
        self,
        turn: Turn,
        *,
        task_id: str,
        answer: Answer | Decisions,
        prepare: Callable[[], Awaitable[None]],
    ) -> AsyncIterator[str]:
        """Answer the widget or review a paused task of the turn's thread asked,
        prepare what it reads first, and stream the rest of its run as start does"""
        run_id = await self._store.create(turn.user_id, turn.thread_id, turn.agent)
        try:
            await prepare()
        except BaseException:
            await self._store.finish(run_id, AgentRunStatus.FAILED, None)
            raise
        self._spawn(
            run_id,
            0,
            task_id,
            turn.handle(turn, run_id, self.answered(turn, run_id, task_id, answer)),
        )
        return self._read(run_id, 0)

    async def _sweep(self, turn: Callable[[RunRecord], Awaitable[Turn]]) -> None:
        """Follow on every run whose process went quiet, starting by reaching the
        harness again"""

        async def events(run: RunRecord) -> AsyncIterator[BaseModel]:
            """The taken-over run's events, its turn looked up first"""
            following = await turn(run)
            async for event in following.handle(
                following,
                run.id,
                self._events(following, run.id, None, run.started_at, run.task_id),
            ):
                yield event

        for run in await self._store.sweep():
            logger.info("run_taken_over", run_id=run.id)
            self._spawn(run.id, run.events, run.task_id, events(run))

    async def _beat(self) -> None:
        """Keep this process's runs its own, and stop writing each one another process
        took over without finishing it"""
        writing = dict(self._writing)
        owned = await self._store.heartbeat()
        for run_id, task in writing.items():
            if run_id not in owned and self._writing.get(run_id) is task:
                logger.warning("run_lost", run_id=run_id)
                task.cancel()

    async def _every(
        self, seconds: float, work: Callable[[], Awaitable[None]], name: str
    ) -> None:
        """Do work every seconds, logging a round that fails"""
        while True:
            await asyncio.sleep(seconds)
            try:
                await work()
            except Exception:
                logger.exception(f"{name}_failed")

    async def recover(self, turn: Callable[[RunRecord], Awaitable[Turn]]) -> None:
        """Take over the runs of processes that went quiet now and every
        sweep_seconds, and heartbeat this process's runs every heartbeat_seconds"""
        await self._sweep(turn)
        self._loops = [
            asyncio.create_task(
                self._every(self._settings.heartbeat_seconds, self._beat, "heartbeat")
            ),
            asyncio.create_task(
                self._every(
                    self._settings.sweep_seconds, partial(self._sweep, turn), "sweep"
                )
            ),
        ]

    async def paused(self, thread_id: str) -> tuple[str, str] | None:
        """The task thread_id's last turn paused on and what it asked: input_required
        or profile_approval; None unless it ended asking the user"""
        return await self._store.paused(thread_id)

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

    async def summary(self, thread_id: str, agent: str) -> ThreadSummary:
        """What the agent remembers of the thread's earlier messages"""
        return await self._ezcareer.summary(thread_id, agent)

    async def update_summary(
        self, thread_id: str, agent: str, update: SummaryUpdate
    ) -> ThreadSummary:
        """Replace the agent's summary of the thread with the user's edit"""
        return await self._ezcareer.update_summary(thread_id, agent, update)

    async def aclose(self) -> None:
        """Stop writing every run, wait for those saving their end, and let the next
        process take the rest over at once, leaving their tasks on the harness"""
        tasks = [*self._loops, *self._writing.values()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, *self._finishing, return_exceptions=True)
        await self._store.release()


__all__ = [
    "AgentRunner",
    "GaveUp",
    "Handle",
    "Tool",
    "ToolError",
    "ToolExecutor",
    "Tools",
    "Turn",
    "WriteTool",
]
