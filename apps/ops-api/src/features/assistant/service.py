from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.ezcareer import Answer, EzcareerClient
from src.core.run_store import RunStore, start_run
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
        runs: RunStore,
    ):
        """Hold the session to commit before a turn runs, the profile the agent reads,
        the settings naming the user's model, the harness, and the store each chat's
        turn streams through"""
        self._session = session
        self._profile = profile
        self._settings = settings
        self._ezcareer = ezcareer
        self._runs = runs

    async def send(self, user_id: UUID, chat_id: UUID, message: ChatMessage) -> str:
        """Start a turn of one of the user's chats in the background and return its run
        id: career-director answers on their model with their profile; Conflict while a
        turn runs"""
        data = await self._profile.agent_profile(user_id)
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        return await start_run(
            self._runs,
            user_id,
            f"{user_id}:{chat_id}",
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
    ) -> str:
        """Answer the widget a paused turn of the chat asked, run the rest of it in the
        background and return its run id; Conflict while a turn runs"""
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        return await start_run(
            self._runs,
            user_id,
            f"{user_id}:{chat_id}",
            self._ezcareer.stream_resume(
                _AGENT,
                str,
                context_id=f"{user_id}:{chat_id}",
                task_id=task_id,
                answer=answer,
                metadata=metadata,
            ),
        )

    async def resume(
        self, user_id: UUID, chat_id: UUID, last_event_id: str | None
    ) -> tuple[str, int]:
        """The chat's current run and how many of its events the client has;
        NotFound when there is none to resume"""
        return await self._runs.resume(f"{user_id}:{chat_id}", last_event_id)

    async def cancel(self, user_id: UUID, chat_id: UUID, task_id: str) -> None:
        """Stop a running turn of one of the user's chats"""
        await self._ezcareer.cancel(_AGENT, task_id, f"{user_id}:{chat_id}")


__all__ = ["AssistantService"]
