from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import suppress
from typing import Literal
from uuid import uuid4

import anyio
import httpx2
from pydantic import BaseModel, TypeAdapter, ValidationError

from src.core.config import EzcareerSettings
from src.core.exceptions import NotFound, ServiceUnavailable
from src.integrations.ezcareer.a2a import (
    DataPart,
    Message,
    SendMessageError,
    SendMessageParams,
    SendMessageRequest,
    SendMessageSuccess,
    StepData,
    StreamSuccess,
    TaskIdParams,
    TaskRequest,
    TaskStatus,
    TaskSuccess,
    TextPart,
)
from src.integrations.ezcareer.schemas import (
    Answer,
    Cancelled,
    Completed,
    Failed,
    InputRequired,
    ModelCatalog,
    Run,
    RunEvent,
    RunMetadata,
    Started,
    StepUpdate,
    Text,
    Thinking,
    Widget,
)


def _new_message(context_id: str, text: str, data: BaseModel) -> Message:
    """A message starting a run on the user's text and its input data"""
    return Message(
        message_id=uuid4().hex,
        context_id=context_id,
        parts=[TextPart(text=text), DataPart(data=data)]
        if text
        else [DataPart(data=data)],
    )


def _answer_message(context_id: str, task_id: str, answer: Answer) -> Message:
    """A message answering the widget a paused task asked"""
    return Message(
        message_id=uuid4().hex,
        context_id=context_id,
        task_id=task_id,
        parts=[DataPart(data=answer)],
    )


def _reason(status: TaskStatus) -> str:
    """Why a task stopped, as the harness put it"""
    return (
        " ".join(part.text for part in status.message.parts if part.text)
        if status.message
        else status.state
    )


class EzcareerClient:
    def __init__(
        self,
        settings: EzcareerSettings,
        transport: httpx2.AsyncBaseTransport | None = None,
    ):
        """One HTTP client for the app's lifetime; tests pass a mock transport"""
        self._http = httpx2.AsyncClient(
            base_url=settings.url,
            timeout=settings.timeout_seconds,
            transport=transport,
        )
        self._run_timeout = settings.run_timeout_seconds

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
        message: Message,
        metadata: RunMetadata | None,
    ) -> Run[R]:
        """POST an A2A SendMessage, with metadata on the request, and read how the
        task ended"""
        request = SendMessageRequest(
            id=uuid4().hex,
            params=SendMessageParams(message=message, metadata=metadata),
        )
        try:
            response = await self._http.post(
                f"a2a/{executable}",
                content=request.model_dump_json(),
                headers={"A2A-Version": "1.0", "Content-Type": "application/json"},
                timeout=self._run_timeout,
            )
            response.raise_for_status()
            outcome = TypeAdapter(SendMessageSuccess | SendMessageError).validate_json(
                response.content
            )
            if isinstance(outcome, SendMessageError):
                return Failed(reason=outcome.error.message)
            task = outcome.result.task
            status = task.status
            match status.state:
                case "TASK_STATE_COMPLETED":
                    [artifact] = task.artifacts
                    [part] = artifact.parts
                    return Completed(
                        reply=TypeAdapter(reply).validate_python(
                            part.data if part.text is None else part.text
                        )
                    )
                case "TASK_STATE_INPUT_REQUIRED" if status.message:
                    return InputRequired(
                        task_id=task.id,
                        widget=Widget.model_validate(status.message.parts[0].data),
                    )
                case _:
                    return Failed(reason=_reason(status))
        except (httpx2.HTTPError, ValueError) as error:
            raise ServiceUnavailable(
                f"ezcareer-harness did not answer {executable}; try again later"
            ) from error

    async def send[R](
        self,
        executable: str,
        reply: type[R],
        *,
        context_id: str,
        data: BaseModel,
        metadata: RunMetadata | None,
        text: str = "",
    ) -> Run[R]:
        """Run a harness executable on the user's text and its input data, on the
        model metadata names; context_id scopes the task to one user"""
        return await self._send_message(
            executable,
            reply,
            _new_message(context_id, text, data),
            metadata,
        )

    async def resume[R](
        self,
        executable: str,
        reply: type[R],
        *,
        context_id: str,
        task_id: str,
        answer: Answer,
        metadata: RunMetadata | None,
    ) -> Run[R]:
        """Send the user's answer to a paused task, which runs on from there on the
        model metadata names"""
        return await self._send_message(
            executable,
            reply,
            _answer_message(context_id, task_id, answer),
            metadata,
        )

    def stream[R](
        self,
        executable: str,
        reply: type[R],
        *,
        context_id: str,
        data: BaseModel,
        metadata: RunMetadata | None,
        text: str = "",
    ) -> AsyncIterator[RunEvent[R]]:
        """Run a harness executable as send does, streaming its start, thinking, text
        and steps, then how it ended"""
        return self._stream(
            executable, reply, _new_message(context_id, text, data), metadata
        )

    def stream_resume[R](
        self,
        executable: str,
        reply: type[R],
        *,
        context_id: str,
        task_id: str,
        answer: Answer,
        metadata: RunMetadata | None,
    ) -> AsyncIterator[RunEvent[R]]:
        """Answer a paused task as resume does, streaming the rest of its run"""
        return self._stream(
            executable, reply, _answer_message(context_id, task_id, answer), metadata
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
        message: Message,
        metadata: RunMetadata | None,
    ) -> AsyncIterator[RunEvent[R]]:
        """POST an A2A SendStreamingMessage and turn its events into run events; a
        stream closed before the run ended cancels the task"""
        request = SendMessageRequest(
            id=uuid4().hex,
            method="SendStreamingMessage",
            params=SendMessageParams(message=message, metadata=metadata),
        )
        task_id = ""
        ended = False
        reply_part = None
        try:
            async with self._http.sse(
                f"a2a/{executable}",
                method="POST",
                content=request.model_dump_json(),
                headers={"A2A-Version": "1.0", "Content-Type": "application/json"},
                timeout=self._run_timeout,
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
                    elif update := result.status_update:
                        status = update.status
                        match status.state:
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
                                yield Failed(reason=_reason(status))
                                return
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
