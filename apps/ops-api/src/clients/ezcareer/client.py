from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Literal
from uuid import UUID, uuid4

import anyio
import httpx2
from pydantic import BaseModel, TypeAdapter, ValidationError

from src.clients.ezcareer.a2a import (
    DataPart,
    Message,
    SendMessageError,
    SendMessageParams,
    SendMessageRequest,
    SendMessageSuccess,
    StatusMessage,
    StepData,
    StreamSuccess,
    TaskIdParams,
    TaskRequest,
    TaskStatus,
    TaskSuccess,
    TextPart,
    UsageData,
)
from src.clients.ezcareer.schemas import (
    Action,
    Answer,
    Cancelled,
    Completed,
    Decisions,
    ExecuteTool,
    Failed,
    InputRequired,
    ModelCatalog,
    NextScreen,
    Published,
    RecordUsage,
    ReviewRequired,
    Run,
    RunEvent,
    RunMetadata,
    Started,
    StepUpdate,
    Text,
    Thinking,
    ToolRequest,
    Usage,
    Widget,
)
from src.core.config import EzcareerSettings
from src.core.exceptions import NotFound, ServiceUnavailable


def _new_message(context_id: str, text: str, data: BaseModel) -> Message:
    """A message starting a run on the user's text and its input data"""
    return Message(
        message_id=uuid4().hex,
        context_id=context_id,
        parts=[TextPart(text=text), DataPart(data=data)]
        if text
        else [DataPart(data=data)],
    )


def _answer_message(context_id: str, task_id: str, answer: BaseModel) -> Message:
    """A message answering a paused task's widget or review"""
    return Message(
        message_id=uuid4().hex,
        context_id=context_id,
        task_id=task_id,
        parts=[DataPart(data=answer)],
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


async def _tool_results(
    context_id: str,
    task_id: str,
    requests: list[tuple[str, ToolRequest]],
    execute_tool: ExecuteTool,
) -> Message:
    """A message resuming a paused task with each tool's result, executed together,
    under the interrupt id that asked for it"""
    results = await asyncio.gather(*(execute_tool(request) for _, request in requests))
    return Message(
        message_id=uuid4().hex,
        context_id=context_id,
        task_id=task_id,
        parts=[
            DataPart(data=result, metadata={"interrupt_id": interrupt_id})
            for (interrupt_id, _), result in zip(requests, results, strict=True)
        ],
    )


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
    """Why a task stopped, as the harness put it, with the screen a data part names"""
    if status.message is None:
        return Failed(reason=status.state)
    parts = status.message.parts
    screen = next(
        (
            p.data["next"]
            for p in parts
            if isinstance(p.data, dict) and p.data.get("next")
        ),
        None,
    )
    return Failed(
        reason=" ".join(part.text for part in parts if part.text),
        next=NextScreen.model_validate(screen) if screen else None,
    )


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
                    headers={"A2A-Version": "1.0", "Content-Type": "application/json"},
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
                        message = await _tool_results(
                            message.context_id, task.id, requests, execute_tool
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
        """Run a harness executable on the user's text and its input data, on the
        model metadata names; context_id scopes the task to one user"""
        return await self._send_message(
            executable,
            reply,
            user_id,
            _new_message(context_id, text, data),
            metadata,
            execute_tool,
        )

    async def resume[R](
        self,
        executable: str,
        reply: type[R],
        *,
        user_id: UUID,
        context_id: str,
        task_id: str,
        answer: Answer,
        metadata: RunMetadata | None,
        execute_tool: ExecuteTool | None = None,
    ) -> Run[R]:
        """Send the user's answer to a paused task, which runs on from there on the
        model metadata names"""
        return await self._send_message(
            executable,
            reply,
            user_id,
            _answer_message(context_id, task_id, answer),
            metadata,
            execute_tool,
        )

    def stream[R](
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
    ) -> AsyncIterator[RunEvent[R]]:
        """Run a harness executable as send does, streaming its start, thinking, text
        and steps, then how it ended"""
        return self._stream(
            executable,
            reply,
            user_id,
            _new_message(context_id, text, data),
            metadata,
            execute_tool,
        )

    def stream_resume[R](
        self,
        executable: str,
        reply: type[R],
        *,
        user_id: UUID,
        context_id: str,
        task_id: str,
        answer: Answer | Decisions,
        metadata: RunMetadata | None,
        execute_tool: ExecuteTool | None = None,
    ) -> AsyncIterator[RunEvent[R]]:
        """Answer a paused task as resume does, or approve or reject the tool calls
        it waits on, streaming the rest of its run"""
        return self._stream(
            executable,
            reply,
            user_id,
            _answer_message(context_id, task_id, answer),
            metadata,
            execute_tool,
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
            headers={"A2A-Version": "1.0", "Content-Type": "application/json"},
        )
        response.raise_for_status()
        return TypeAdapter(TaskSuccess | SendMessageError).validate_json(
            response.content
        )

    async def _stream[R](
        self,
        executable: str,
        reply: type[R],
        user_id: UUID,
        message: Message,
        metadata: RunMetadata | None,
        execute_tool: ExecuteTool | None,
    ) -> AsyncIterator[RunEvent[R]]:
        """POST an A2A SendStreamingMessage and turn its events into run events,
        executing any tool it pauses on and keeping each model call's usage; a
        stream closed early cancels the task"""
        task_id = ""
        ended = False
        reply_part = None
        try:
            while message is not None:
                request = SendMessageRequest(
                    id=uuid4().hex,
                    method="SendStreamingMessage",
                    params=SendMessageParams(message=message, metadata=metadata),
                )
                next_message: Message | None = None
                async with self._http.sse(
                    f"a2a/{executable}",
                    method="POST",
                    content=request.model_dump_json(),
                    headers={"A2A-Version": "1.0", "Content-Type": "application/json"},
                    timeout=self.run_timeout_seconds,
                ) as source:
                    async for event in source:
                        outcome = TypeAdapter(
                            StreamSuccess | SendMessageError
                        ).validate_json(event.data)
                        if isinstance(outcome, SendMessageError):
                            ended = True
                            yield Failed(reason=outcome.error.message)
                            return
                        result = outcome.result
                        if not task_id:
                            task_id = (
                                result.task.id
                                if result.task
                                else result.status_update.task_id
                                if result.status_update
                                else result.artifact_update.task_id
                                if result.artifact_update
                                else ""
                            )
                            yield Started(task_id=task_id)
                        if update := result.artifact_update:
                            artifact = update.artifact
                            text = "".join(part.text or "" for part in artifact.parts)
                            if artifact.name == "thinking":
                                yield Thinking(turn=artifact.artifact_id, text=text)
                            elif artifact.name == "text":
                                yield Text(turn=artifact.artifact_id, text=text)
                            elif artifact.name == executable:
                                [reply_part] = artifact.parts
                            else:
                                [part] = artifact.parts
                                yield Published(name=artifact.name, data=part.data)
                        elif update := result.status_update:
                            status = update.status
                            match status.state:
                                case "TASK_STATE_WORKING" if usage := _usage(
                                    status.message
                                ):
                                    await self._record_usage(
                                        user_id,
                                        message.context_id,
                                        update.task_id,
                                        usage,
                                    )
                                case "TASK_STATE_WORKING" if status.message:
                                    yield StepUpdate(
                                        step=StepData.model_validate(
                                            status.message.parts[0].data
                                        ).step
                                    )
                                case "TASK_STATE_COMPLETED" if reply_part:
                                    ended = True
                                    yield Completed(
                                        reply=TypeAdapter(reply).validate_python(
                                            reply_part.data
                                            if reply_part.text is None
                                            else reply_part.text
                                        )
                                    )
                                    return
                                case "TASK_STATE_INPUT_REQUIRED" if execute_tool and (
                                    asked := _tool_requests(status)
                                ):
                                    next_message = await _tool_results(
                                        message.context_id,
                                        update.task_id,
                                        asked,
                                        execute_tool,
                                    )
                                case "TASK_STATE_INPUT_REQUIRED" if review := _review(
                                    update.task_id, status
                                ):
                                    ended = True
                                    yield review
                                    return
                                case "TASK_STATE_INPUT_REQUIRED" if status.message:
                                    ended = True
                                    yield InputRequired(
                                        task_id=update.task_id,
                                        widget=Widget.model_validate(
                                            status.message.parts[0].data
                                        ),
                                    )
                                    return
                                case "TASK_STATE_CANCELED":
                                    ended = True
                                    yield Cancelled()
                                    return
                                case "TASK_STATE_FAILED" | "TASK_STATE_REJECTED":
                                    ended = True
                                    yield _failed(status)
                                    return
                message = next_message
            ended = True
            yield Failed(reason=f"ezcareer-harness stopped answering {executable}")
        except (httpx2.HTTPError, ValueError):
            ended = True
            yield Failed(
                reason=f"ezcareer-harness did not answer {executable}; try again later"
            )
        finally:
            if task_id and not ended:
                with (
                    anyio.CancelScope(shield=True),
                    suppress(httpx2.HTTPError, ValueError),
                ):
                    await self._task_rpc(executable, "CancelTask", task_id)

    async def aclose(self) -> None:
        """Close the HTTP client's connections"""
        await self._http.aclose()


__all__ = ["EzcareerClient"]
