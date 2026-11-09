from __future__ import annotations

from uuid import uuid4

import httpx2
from pydantic import BaseModel, TypeAdapter, ValidationError

from src.core.config import EzcareerSettings
from src.core.exceptions import ServiceUnavailable
from src.integrations.ezcareer.a2a import (
    DataPart,
    Message,
    SendMessageError,
    SendMessageParams,
    SendMessageRequest,
    SendMessageSuccess,
    TextPart,
)
from src.integrations.ezcareer.schemas import (
    Answer,
    Completed,
    Failed,
    InputRequired,
    ModelCatalog,
    Run,
    Widget,
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
        self, executable: str, reply: type[R], message: Message
    ) -> Run[R]:
        """POST an A2A SendMessage and read how the task ended"""
        request = SendMessageRequest(
            id=uuid4().hex, params=SendMessageParams(message=message)
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
                    return Failed(
                        reason=" ".join(
                            part.text for part in status.message.parts if part.text
                        )
                        if status.message
                        else status.state
                    )
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
        text: str = "",
    ) -> Run[R]:
        """Run a harness executable on the user's text and its input data;
        context_id scopes the task to one user, so a resume must match it"""
        return await self._send_message(
            executable,
            reply,
            Message(
                message_id=uuid4().hex,
                context_id=context_id,
                parts=[TextPart(text=text), DataPart(data=data)]
                if text
                else [DataPart(data=data)],
            ),
        )

    async def resume[R](
        self,
        executable: str,
        reply: type[R],
        *,
        context_id: str,
        task_id: str,
        answer: Answer,
    ) -> Run[R]:
        """Send the user's answer to a paused task, which runs on from there"""
        return await self._send_message(
            executable,
            reply,
            Message(
                message_id=uuid4().hex,
                context_id=context_id,
                task_id=task_id,
                parts=[DataPart(data=answer)],
            ),
        )

    async def aclose(self) -> None:
        """Close the HTTP client's connections"""
        await self._http.aclose()


__all__ = ["EzcareerClient"]
