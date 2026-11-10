from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.features.assistant.schemas import ChatMessage
from src.features.profile import ProfileService
from src.features.settings import SettingsService
from src.integrations.ezcareer import Answer, EzcareerClient, RunEvent

_AGENT = "career-director"


class AssistantService:
    def __init__(
        self,
        session: AsyncSession,
        profile: ProfileService,
        settings: SettingsService,
        ezcareer: EzcareerClient,
    ):
        """Hold the session to commit before a turn runs, the profile the agent reads,
        the settings naming the user's model, and the harness it runs on"""
        self._session = session
        self._profile = profile
        self._settings = settings
        self._ezcareer = ezcareer

    async def send(
        self, user_id: UUID, chat_id: UUID, message: ChatMessage
    ) -> AsyncIterator[RunEvent[str]]:
        """Start a turn of one of the user's chats and stream it: career-director
        answers on their model with their profile, with no transaction open meanwhile"""
        data = await self._profile.agent_profile(user_id)
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        return self._ezcareer.stream(
            _AGENT,
            str,
            context_id=f"{user_id}:{chat_id}",
            text=message.text,
            data=data,
            metadata=metadata,
        )

    async def answer(
        self, user_id: UUID, chat_id: UUID, task_id: str, answer: Answer
    ) -> AsyncIterator[RunEvent[str]]:
        """Answer the widget a paused turn of the chat asked, and stream the rest of it"""
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        return self._ezcareer.stream_resume(
            _AGENT,
            str,
            context_id=f"{user_id}:{chat_id}",
            task_id=task_id,
            answer=answer,
            metadata=metadata,
        )

    async def cancel(self, user_id: UUID, chat_id: UUID, task_id: str) -> None:
        """Stop a running turn of one of the user's chats"""
        await self._ezcareer.cancel(_AGENT, task_id, f"{user_id}:{chat_id}")


__all__ = ["AssistantService"]
