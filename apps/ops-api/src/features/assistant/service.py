from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.ezcareer import Answer, EzcareerClient, RunEvent, RunStream
from src.core.config import EzcareerSettings
from src.core.exceptions import Conflict, NotFound
from src.features.assistant.schemas import ChatMessage
from src.features.profile import ProfileService
from src.features.settings import SettingsService

_AGENT = "career-director"


class AssistantService:
    def __init__(
        self,
        session: AsyncSession,
        profile: ProfileService,
        settings: SettingsService,
        ezcareer: EzcareerClient,
        runs: dict[str, RunStream],
        config: EzcareerSettings,
    ):
        """Hold the session to commit before a turn runs, the profile the agent reads,
        the settings naming the user's model, the harness, and each chat's turn"""
        self._session = session
        self._profile = profile
        self._settings = settings
        self._ezcareer = ezcareer
        self._runs = runs
        self._config = config

    def _idle(self, key: str) -> None:
        """Conflict while the chat's turn is still running"""
        if (run := self._runs.get(key)) and not run.done:
            raise Conflict("Wait for the current reply to finish")

    def _start(self, key: str, events: AsyncIterator[RunEvent[str]]) -> RunStream:
        """Run a turn of the chat in the background, replacing its last one"""
        self._runs[key] = RunStream(events, self._config.stream_retry_ms)
        return self._runs[key]

    async def send(
        self, user_id: UUID, chat_id: UUID, message: ChatMessage
    ) -> RunStream:
        """Start a turn of one of the user's chats in the background: career-director
        answers on their model with their profile; Conflict while a turn runs"""
        key = f"{user_id}:{chat_id}"
        self._idle(key)
        data = await self._profile.agent_profile(user_id)
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        return self._start(
            key,
            self._ezcareer.stream(
                _AGENT,
                str,
                context_id=f"{user_id}:{chat_id}",
                text=message.text,
                data=data,
                metadata=metadata,
            ),
        )

    async def answer(
        self, user_id: UUID, chat_id: UUID, task_id: str, answer: Answer
    ) -> RunStream:
        """Answer the widget a paused turn of the chat asked, and run the rest of it in
        the background; Conflict while a turn runs"""
        key = f"{user_id}:{chat_id}"
        self._idle(key)
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        return self._start(
            key,
            self._ezcareer.stream_resume(
                _AGENT,
                str,
                context_id=f"{user_id}:{chat_id}",
                task_id=task_id,
                answer=answer,
                metadata=metadata,
            ),
        )

    def resume(
        self, user_id: UUID, chat_id: UUID, last_event_id: str | None
    ) -> tuple[RunStream, int]:
        """The chat's current turn and how many of its events the client has;
        NotFound when there is none to resume"""
        run = self._runs.get(f"{user_id}:{chat_id}")
        after = (
            run.resume_point(last_event_id)
            if run and run.resumable(self._config.replay_ttl_seconds)
            else None
        )
        if run is None or after is None:
            raise NotFound("There is no reply to resume")
        return run, after

    async def cancel(self, user_id: UUID, chat_id: UUID, task_id: str) -> None:
        """Stop a running turn of one of the user's chats"""
        await self._ezcareer.cancel(_AGENT, task_id, f"{user_id}:{chat_id}")


__all__ = ["AssistantService"]
