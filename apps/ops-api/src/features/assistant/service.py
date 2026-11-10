from __future__ import annotations

from collections.abc import AsyncIterator
from functools import partial
from uuid import UUID

from pydantic import BaseModel, ValidationError

from src.clients.ezcareer import (
    Answer,
    DataRequest,
    EzcareerClient,
    Published,
    RunEvent,
)
from src.core.logging import get_logger
from src.core.runner import Runner
from src.features.assistant.schemas import ChatMessage
from src.features.documents import ChangesetArtifact, DocumentService
from src.features.inbox import InboxService
from src.features.profile import ProfileService
from src.features.settings import SettingsService

_AGENT = "career-director"

logger = get_logger(__name__)


class AssistantService:
    def __init__(
        self,
        profile: ProfileService,
        settings: SettingsService,
        documents: DocumentService,
        inbox: InboxService,
        ezcareer: EzcareerClient,
        runner: Runner,
    ):
        """Hold the profile, settings, documents, inbox and harness a turn uses, and
        the runner it runs on"""
        self._profile = profile
        self._settings = settings
        self._documents = documents
        self._inbox = inbox
        self._ezcareer = ezcareer
        self._runner = runner

    async def _turn(
        self, user_id: UUID, events: AsyncIterator[RunEvent[str]]
    ) -> AsyncIterator[BaseModel]:
        """A turn's events as the browser gets them: a changeset career-director
        publishes is stored and announced, and other published artifacts are not sent"""
        async for event in events:
            if not isinstance(event, Published):
                yield event
            elif event.name == "changeset":
                try:
                    artifact = ChangesetArtifact.model_validate(event.data)
                except ValidationError as error:
                    logger.warning("changeset_skipped", reason=str(error))
                    continue
                if proposed := await self._documents.propose_from_run(
                    user_id, artifact.document_id, artifact.changeset
                ):
                    yield proposed

    async def _answer(self, user_id: UUID, request: DataRequest) -> BaseModel:
        """Answer a paused turn's data request from the inbox or the documents"""
        if request.fetch in ("thread", "free_slots"):
            return await self._inbox.answer_data_request(user_id, request)
        return await self._documents.answer_data_request(user_id, request)

    async def send(
        self, user_id: UUID, chat_id: UUID, message: ChatMessage
    ) -> AsyncIterator[str]:
        """Start a turn of the user's chat and return its events as they come; Conflict
        while a turn runs"""
        thread_id = f"{user_id}:{chat_id}"
        data = await self._profile.agent_profile(user_id)
        metadata = await self._settings.run_metadata(user_id)
        return await self._runner.start_task(
            user_id,
            thread_id,
            _AGENT,
            self._turn(
                user_id,
                self._ezcareer.stream(
                    _AGENT,
                    str,
                    user_id=user_id,
                    context_id=thread_id,
                    text=message.text,
                    data=data,
                    metadata=metadata,
                    answer_data_request=partial(self._answer, user_id),
                ),
            ),
        )

    async def answer(
        self, user_id: UUID, chat_id: UUID, task_id: str, answer: Answer
    ) -> AsyncIterator[str]:
        """Answer the widget a paused turn of the chat asked and return the rest of
        the turn's events as they come; Conflict while a turn runs"""
        thread_id = f"{user_id}:{chat_id}"
        metadata = await self._settings.run_metadata(user_id)
        return await self._runner.start_task(
            user_id,
            thread_id,
            _AGENT,
            self._turn(
                user_id,
                self._ezcareer.stream_resume(
                    _AGENT,
                    str,
                    user_id=user_id,
                    context_id=thread_id,
                    task_id=task_id,
                    answer=answer,
                    metadata=metadata,
                    answer_data_request=partial(self._answer, user_id),
                ),
            ),
        )

    async def resume(
        self, user_id: UUID, chat_id: UUID, last_event_id: str | None
    ) -> AsyncIterator[str]:
        """The chat's current turn after the Last-Event-ID the client last saw;
        NotFound when there is none to resume"""
        return await self._runner.resume(f"{user_id}:{chat_id}", last_event_id)

    async def cancel(self, user_id: UUID, chat_id: UUID, task_id: str) -> None:
        """Stop a running turn of one of the user's chats"""
        await self._ezcareer.cancel(_AGENT, task_id, f"{user_id}:{chat_id}")


__all__ = ["AssistantService"]
