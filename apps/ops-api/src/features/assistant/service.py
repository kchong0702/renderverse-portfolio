from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from src.clients.ezcareer import Answer, EzcareerClient
from src.core.runner import Runner
from src.features.assistant.schemas import ChatMessage
from src.features.profile import ProfileService
from src.features.settings import SettingsService

_AGENT = "career-director"


class AssistantService:
    def __init__(
        self,
        profile: ProfileService,
        settings: SettingsService,
        ezcareer: EzcareerClient,
        runner: Runner,
    ):
        """Hold the profile, settings and harness a turn uses, and the runner it runs
        on"""
        self._profile = profile
        self._settings = settings
        self._ezcareer = ezcareer
        self._runner = runner

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
            self._ezcareer.stream(
                _AGENT,
                str,
                user_id=user_id,
                context_id=thread_id,
                text=message.text,
                data=data,
                metadata=metadata,
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
            self._ezcareer.stream_resume(
                _AGENT,
                str,
                user_id=user_id,
                context_id=thread_id,
                task_id=task_id,
                answer=answer,
                metadata=metadata,
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
