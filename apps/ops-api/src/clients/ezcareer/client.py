from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Literal, NamedTuple
from uuid import UUID, uuid4

import httpx2
from pydantic import BaseModel, TypeAdapter, ValidationError

from src.clients.ezcareer.a2a import (
    Artifact,
    DataPart,
    ListTasksParams,
    ListTasksRequest,
    ListTasksSuccess,
    Message,
    SendMessageConfiguration,
    SendMessageError,
    SendMessageParams,
    SendMessageRequest,
    SendMessageSuccess,
    StatusMessage,
    StepData,
    StreamSuccess,
    Task,
    TaskIdParams,
    TaskRequest,
    TaskStatus,
    TaskSuccess,
    TextPart,
    UsageData,
)
from src.clients.ezcareer.exceptions import HarnessUnreachable
from src.clients.ezcareer.schemas import (
    Action,
    Answer,
    Cancelled,
    Completed,
    Decisions,
    ExecuteTool,
    Failed,
    InputRequired,
    MessageMetadata,
    ModelCatalog,
    NextScreen,
    Published,
    RecordUsage,
    Replied,
    ReviewRequired,
    Run,
    RunEvent,
    RunMetadata,
    StepUpdate,
    SummaryUpdate,
    Text,
    Thinking,
    ThreadSummary,
    ToolRequest,
    ToolsRequested,
    Usage,
    Widget,
)
from src.core.config import EzcareerSettings
from src.core.exceptions import Conflict, NotFound, ServiceUnavailable

_HEADERS = {"A2A-Version": "1.0", "Content-Type": "application/json"}


class TaskState(NamedTuple):
    task_id: str
    """The task"""

    events: list[RunEvent[str] | ToolsRequested]
    """What its status says: nothing while it works, the tools it asks for, or the
    message ending the turn and how it ended"""


def _new_message(
    context_id: str,
    message_id: str,
    text: str,
    data: BaseModel,
    metadata: MessageMetadata | None = None,
) -> Message:
    """A message starting a run on the user's text and its input data"""
    return Message(
        message_id=message_id,
        context_id=context_id,
        parts=[TextPart(text=text), DataPart(data=data)]
        if text
        else [DataPart(data=data)],
        metadata=metadata,
    )


def _answer_message(context_id: str, task_id: str, answer: BaseModel) -> Message:
    """A message answering a paused task's widget or review"""
    return Message(
        message_id=uuid4().hex,
        context_id=context_id,
        task_id=task_id,
        parts=[DataPart(data=answer)],
    )


def _results_message(
    context_id: str, task_id: str, results: list[tuple[str, BaseModel]]
) -> Message:
    """A message resuming a paused task with each tool's result, under the interrupt
    id that asked for it"""
    return Message(
        message_id=uuid4().hex,
        context_id=context_id,
        task_id=task_id,
        parts=[
            DataPart(data=result, metadata={"interrupt_id": interrupt_id})
            for interrupt_id, result in results
        ],
    )


def _tool_requests(status: TaskStatus) -> list[tuple[str, ToolRequest]]:
    """Each tool a paused task asks ops-api to execute, under its interrupt id; empty
    when the task waits for anything else"""
    parts = status.message.parts if status.message else []
    requests = [
        (str(part.metadata["interrupt_id"]), ToolRequest.model_validate(part.data))
        for part in parts
        if isinstance(part.data, dict)
        and "execute_tool" in part.data
        and part.metadata
        and "interrupt_id" in part.metadata
    ]
    return requests if len(requests) == len(parts) else []


def _review(task_id: str, status: TaskStatus) -> ReviewRequired | None:
    """The tool calls a paused task waits for the user to approve, or None when it
    asks something else"""
    data = status.message.parts[0].data if status.message else None
    return (
        ReviewRequired(
            task_id=task_id,
            actions=TypeAdapter(list[Action]).validate_python(data["action_requests"]),
        )
        if isinstance(data, dict) and "action_requests" in data
        else None
    )


def _usage(message: StatusMessage | None) -> Usage | None:
    """The model call's usage a status message carries, if it carries one"""
    data = message.parts[0].data if message else None
    return (
        UsageData.model_validate(data).usage
        if isinstance(data, dict) and "usage" in data
        else None
    )


def _failed(status: TaskStatus) -> Failed:
    """Why a task stopped, as the harness put it or in plain words when it gave no
    reason, with the screen a data part names"""
    parts = status.message.parts if status.message else []
    screen = next(
        (
            p.data["next"]
            for p in parts
            if isinstance(p.data, dict) and p.data.get("next")
        ),
        None,
    )
    return Failed(
        reason=" ".join(part.text for part in parts if part.text)
        or "The assistant hit an error. Send your message again.",
        next=NextScreen.model_validate(screen) if screen else None,
    )


def _reply(executable: str, artifacts: list[Artifact]) -> str | None:
    """The text of the executable's reply artifact, if the task has one yet"""
    return next(
        (
            "".join(part.text or "" for part in artifact.parts)
            for artifact in artifacts
            if artifact.name == executable
        ),
        None,
    )


def _ended(
    task_id: str, status: TaskStatus, reply: str | None
) -> list[RunEvent[str] | ToolsRequested]:
    """What a task's status says about its run: nothing while it works, the tools it
    asks ops-api to execute, or the message ending the turn and how it ended"""
    message = status.message
    match status.state:
        case "TASK_STATE_SUBMITTED" | "TASK_STATE_WORKING":
            return []
        case "TASK_STATE_INPUT_REQUIRED" if requests := _tool_requests(status):
            return [ToolsRequested(task_id=task_id, requests=requests)]
        case "TASK_STATE_INPUT_REQUIRED" if review := _review(task_id, status):
            ended: RunEvent[str] = review
        case "TASK_STATE_INPUT_REQUIRED" if message:
            ended = InputRequired(
                task_id=task_id, widget=Widget.model_validate(message.parts[0].data)
            )
        case "TASK_STATE_COMPLETED":
            text = (
                "".join(part.text for part in message.parts if part.text)
                if message
                else ""
            )
            ended = Completed(reply=text or reply or "")
        case "TASK_STATE_CANCELED":
            ended = Cancelled()
        case _:
            ended = _failed(status)
    replied = (
        [
            Replied(
                message_id=message.message_id,
                agent=(message.metadata or {}).get("agent"),
                document_id=(message.metadata or {}).get("document_id"),
            )
        ]
        if message and message.message_id
        else []
    )
    return [*replied, ended]


class EzcareerClient:
    def __init__(
        self,
        settings: EzcareerSettings,
        record_usage: RecordUsage,
        transport: httpx2.AsyncBaseTransport | None = None,
    ):
        """One HTTP client for the app's lifetime, keeping each model call's usage with
        record_usage; tests pass a mock transport"""
        self._http = httpx2.AsyncClient(
            base_url=settings.url,
            timeout=settings.timeout_seconds,
            transport=transport,
        )
        self.run_timeout_seconds = settings.run_timeout_seconds
        self._record_usage = record_usage

    async def models(self) -> ModelCatalog:
        """The models ezcareer-harness offers, by provider"""
        try:
            response = await self._http.get("models")
            response.raise_for_status()
            return ModelCatalog.model_validate_json(response.content)
        except (httpx2.HTTPError, ValidationError) as error:
            raise ServiceUnavailable(
                "ezcareer-harness did not return its models; try again later"
            ) from error

    async def _send_message[R](
        self,
        executable: str,
        reply: type[R],
        user_id: UUID,
        message: Message,
        metadata: RunMetadata | None,
        execute_tool: ExecuteTool | None,
    ) -> Run[R]:
        """POST an A2A SendMessage, with metadata on the request, executing any tool
        the task pauses on, keeping the usage its history reports, and read how the
        task ended"""
        recorded: set[str] = set()
        try:
            while True:
                response = await self._http.post(
                    f"a2a/{executable}",
                    content=SendMessageRequest(
                        id=uuid4().hex,
                        params=SendMessageParams(message=message, metadata=metadata),
                    ).model_dump_json(),
                    headers=_HEADERS,
                    timeout=self.run_timeout_seconds,
                )
                response.raise_for_status()
                outcome = TypeAdapter(
                    SendMessageSuccess | SendMessageError
                ).validate_json(response.content)
                if isinstance(outcome, SendMessageError):
                    return Failed(reason=outcome.error.message)
                task = outcome.result.task
                for entry in task.history:
                    if entry.message_id not in recorded and (usage := _usage(entry)):
                        recorded.add(entry.message_id)
                        await self._record_usage(
                            user_id, message.context_id, task.id, usage
                        )
                status = task.status
                match status.state:
                    case "TASK_STATE_COMPLETED":
                        [artifact] = [a for a in task.artifacts if a.name == executable]
                        [part] = artifact.parts
                        return Completed(
                            reply=TypeAdapter(reply).validate_python(
                                part.data if part.text is None else part.text
                            )
                        )
                    case "TASK_STATE_INPUT_REQUIRED" if execute_tool and (
                        requests := _tool_requests(status)
                    ):
                        results = await asyncio.gather(
                            *(
                                execute_tool(task.id, interrupt_id, request)
                                for interrupt_id, request in requests
                            )
                        )
                        message = _results_message(
                            message.context_id,
                            task.id,
                            [
                                (interrupt_id, result)
                                for (interrupt_id, _), result in zip(
                                    requests, results, strict=True
                                )
                            ],
                        )
                    case "TASK_STATE_INPUT_REQUIRED" if status.message:
                        return InputRequired(
                            task_id=task.id,
                            widget=Widget.model_validate(status.message.parts[0].data),
                        )
                    case _:
                        return _failed(status)
        except (httpx2.HTTPError, ValueError) as error:
            raise ServiceUnavailable(
                f"ezcareer-harness did not answer {executable}; try again later"
            ) from error

    async def send[R](
        self,
        executable: str,
        reply: type[R],
        *,
        user_id: UUID,
        context_id: str,
        data: BaseModel,
        metadata: RunMetadata | None,
        text: str = "",
        execute_tool: ExecuteTool | None = None,
    ) -> Run[R]:
        """Run a harness executable on the user's text and input data and wait for how
        it ended; context_id scopes the task to one user"""
        return await self._send_message(
            executable,
            reply,
            user_id,
            _new_message(context_id, uuid4().hex, text, data),
            metadata,
            execute_tool,
        )

    async def _submit(
        self, executable: str, message: Message, metadata: RunMetadata | None
    ) -> str | Failed:
        """SendMessage answered as soon as the task exists: its id, or why the harness
        refused; HarnessUnreachable when it can't be reached"""
        try:
            response = await self._http.post(
                f"a2a/{executable}",
                content=SendMessageRequest(
                    id=uuid4().hex,
                    params=SendMessageParams(
                        message=message,
                        metadata=metadata,
                        configuration=SendMessageConfiguration(return_immediately=True),
                    ),
                ).model_dump_json(),
                headers=_HEADERS,
            )
            response.raise_for_status()
        except httpx2.HTTPError as error:
            raise HarnessUnreachable(
                f"ezcareer-harness did not take the message for {executable}"
            ) from error
        try:
            outcome = TypeAdapter(SendMessageSuccess | SendMessageError).validate_json(
                response.content
            )
        except ValidationError:
            return Failed(
                reason=f"ezcareer-harness did not answer {executable}; try again later"
            )
        if isinstance(outcome, SendMessageError):
            return Failed(reason=outcome.error.message)
        return outcome.result.task.id

    async def start(
        self,
        executable: str,
        *,
        context_id: str,
        message_id: str,
        text: str,
        sent: MessageMetadata,
        data: BaseModel,
        metadata: RunMetadata | None,
    ) -> str | Failed:
        """Start an agent's task on the user's message and its input data; the task's id
        or why the harness refused it"""
        return await self._submit(
            executable,
            _new_message(context_id, message_id, text, data, sent),
            metadata,
        )

    async def answer(
        self,
        executable: str,
        *,
        context_id: str,
        task_id: str,
        answer: Answer | Decisions,
        metadata: RunMetadata | None,
    ) -> str | Failed:
        """Send the user's answer or decisions to a paused task, which runs on, and
        return its id or why the harness refused the answer"""
        return await self._submit(
            executable, _answer_message(context_id, task_id, answer), metadata
        )

    async def results(
        self,
        executable: str,
        *,
        context_id: str,
        task_id: str,
        results: list[tuple[str, BaseModel]],
        metadata: RunMetadata | None,
    ) -> str | Failed:
        """Send a paused task the results of the tools it asked for, which it runs on
        with, and return its id or why the harness refused them"""
        return await self._submit(
            executable, _results_message(context_id, task_id, results), metadata
        )

    async def follow(
        self, executable: str, user_id: UUID, context_id: str, task_id: str
    ) -> AsyncIterator[RunEvent[str] | ToolsRequested]:
        """A task's events from where it stands until it asks for tools, pauses or
        ends, keeping each call's usage; HarnessUnreachable when the stream breaks"""
        reply = None
        try:
            async with self._http.sse(
                f"a2a/{executable}",
                method="POST",
                content=TaskRequest(
                    id=uuid4().hex,
                    method="SubscribeToTask",
                    params=TaskIdParams(id=task_id),
                ).model_dump_json(),
                headers=_HEADERS,
                timeout=self.run_timeout_seconds,
            ) as source:
                async for event in source:
                    outcome = TypeAdapter(
                        StreamSuccess | SendMessageError
                    ).validate_json(event.data)
                    if isinstance(outcome, SendMessageError):
                        state = await self.state(executable, task_id, context_id, None)
                        for ended in (
                            state.events
                            if state and state.events
                            else [Failed(reason=outcome.error.message)]
                        ):
                            yield ended
                        return
                    result = outcome.result
                    if result.task:
                        status = result.task.status
                        reply = _reply(executable, result.task.artifacts) or reply
                    elif update := result.artifact_update:
                        artifact = update.artifact
                        text = "".join(part.text or "" for part in artifact.parts)
                        if artifact.name == "thinking":
                            yield Thinking(turn=artifact.artifact_id, text=text)
                        elif artifact.name == "text":
                            yield Text(turn=artifact.artifact_id, text=text)
                        elif artifact.name == executable:
                            reply = text
                        else:
                            [part] = artifact.parts
                            yield Published(name=artifact.name, data=part.data)
                        continue
                    elif update := result.status_update:
                        status = update.status
                        if status.state == "TASK_STATE_WORKING" and (
                            usage := _usage(status.message)
                        ):
                            await self._record_usage(
                                user_id, context_id, task_id, usage
                            )
                            continue
                        if status.state == "TASK_STATE_WORKING" and status.message:
                            yield StepUpdate(
                                step=StepData.model_validate(
                                    status.message.parts[0].data
                                ).step
                            )
                            continue
                    else:
                        continue
                    if events := _ended(task_id, status, reply):
                        for ended in events:
                            yield ended
                        return
        except httpx2.SSEError as error:
            state = await self.state(executable, task_id, context_id, None)
            if state is None or not state.events:
                raise HarnessUnreachable(
                    f"ezcareer-harness would not stream the {executable} task"
                ) from error
            for ended in state.events:
                yield ended
            return
        except httpx2.HTTPError as error:
            raise HarnessUnreachable(
                f"The {executable} stream broke before the task paused or ended"
            ) from error
        except ValidationError:
            yield Failed(
                reason=f"ezcareer-harness did not answer {executable}; try again later"
            )
            return
        raise HarnessUnreachable(
            f"The {executable} stream ended before the task paused or ended"
        )

    async def state(
        self,
        executable: str,
        task_id: str | None,
        context_id: str,
        since: datetime | None,
    ) -> TaskState | None:
        """Where a task stands, by GetTask, or ListTasks on the context since `since`
        when its id is unknown; None when there is no such task"""
        try:
            if task_id:
                found = await self._task_rpc(executable, "GetTask", task_id)
                task = found.result if isinstance(found, TaskSuccess) else None
            else:
                task = await self._find(executable, context_id, since)
        except (httpx2.HTTPError, ValueError) as error:
            raise HarnessUnreachable(
                f"ezcareer-harness did not say where the {executable} task stands"
            ) from error
        if task is None:
            return None
        return TaskState(
            task_id=task.id,
            events=_ended(task.id, task.status, _reply(executable, task.artifacts)),
        )

    async def _find(
        self, executable: str, context_id: str, since: datetime | None
    ) -> Task | None:
        """The context's latest task whose status changed since `since`, if any"""
        if since is None:
            return None
        response = await self._http.post(
            f"a2a/{executable}",
            content=ListTasksRequest(
                id=uuid4().hex,
                params=ListTasksParams(
                    context_id=context_id, status_timestamp_after=since
                ),
            ).model_dump_json(),
            headers=_HEADERS,
        )
        response.raise_for_status()
        found = TypeAdapter(ListTasksSuccess | SendMessageError).validate_json(
            response.content
        )
        return (
            found.result.tasks[0]
            if isinstance(found, ListTasksSuccess) and found.result.tasks
            else None
        )

    async def cancel(self, executable: str, task_id: str, context_id: str) -> None:
        """Stop a task of the context; NotFound when it is another context's, and a
        task that already ended stays as it is"""
        try:
            task = await self._task_rpc(executable, "GetTask", task_id)
            if (
                not isinstance(task, TaskSuccess)
                or task.result.context_id != context_id
            ):
                raise NotFound("No such task")
            await self._task_rpc(executable, "CancelTask", task_id)
        except (httpx2.HTTPError, ValueError) as error:
            raise ServiceUnavailable(
                f"ezcareer-harness did not stop {executable}; try again later"
            ) from error

    async def _task_rpc(
        self, executable: str, method: Literal["GetTask", "CancelTask"], task_id: str
    ) -> TaskSuccess | SendMessageError:
        """Read or cancel one of the executable's tasks"""
        response = await self._http.post(
            f"a2a/{executable}",
            content=TaskRequest(
                id=uuid4().hex, method=method, params=TaskIdParams(id=task_id)
            ).model_dump_json(),
            headers=_HEADERS,
        )
        response.raise_for_status()
        return TypeAdapter(TaskSuccess | SendMessageError).validate_json(
            response.content
        )

    async def summary(self, thread_id: str, agent: str) -> ThreadSummary:
        """What the agent remembers of a thread's earlier messages"""
        try:
            response = await self._http.get(
                f"threads/{thread_id}/summary", params={"agent": agent}
            )
            response.raise_for_status()
            return ThreadSummary.model_validate_json(response.content)
        except (httpx2.HTTPError, ValidationError) as error:
            raise ServiceUnavailable(
                "ezcareer-harness did not return the summary; try again later"
            ) from error

    async def update_summary(
        self, thread_id: str, agent: str, update: SummaryUpdate
    ) -> ThreadSummary:
        """Replace the agent's summary of a thread with the user's edit; NotFound
        before the agent summarised it, Conflict while a reply runs or waits"""
        try:
            response = await self._http.put(
                f"threads/{thread_id}/summary",
                params={"agent": agent},
                content=update.model_dump_json(),
                headers={"Content-Type": "application/json"},
            )
            if response.status_code == 404:
                raise NotFound("There is no summary to edit yet")
            if response.status_code == 409:
                raise Conflict(
                    "Wait for the current reply to finish before editing the summary"
                )
            response.raise_for_status()
            return ThreadSummary.model_validate_json(response.content)
        except (httpx2.HTTPError, ValidationError) as error:
            raise ServiceUnavailable(
                "ezcareer-harness did not save the summary; try again later"
            ) from error

    async def aclose(self) -> None:
        """Close the HTTP client's connections"""
        await self._http.aclose()


__all__ = ["EzcareerClient", "TaskState"]
