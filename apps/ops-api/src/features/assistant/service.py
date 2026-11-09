from __future__ import annotations

from uuid import UUID

from src.features.assistant.schemas import ChatMessage
from src.features.profile import ProfileService
from src.features.settings import SettingsService
from src.integrations.ezcareer import Answer, EzcareerClient, Run

_AGENT = "career-director"


class AssistantService:
    def __init__(
        self,
        profile: ProfileService,
        settings: SettingsService,
        ezcareer: EzcareerClient,
    ):
        """Keep the profile the agent reads, the settings naming the user's model,
        and the harness it runs on"""
        self._profile = profile
        self._settings = settings
        self._ezcareer = ezcareer

    async def send(
        self, user_id: UUID, chat_id: UUID, message: ChatMessage
    ) -> Run[str]:
        """Start a turn of one of the user's chats: career-director answers on their
        model with their profile's facts and preferences, and the chat's earlier turns"""
        return await self._ezcareer.send(
            _AGENT,
            str,
            context_id=f"{user_id}:{chat_id}",
            text=message.text,
            data=await self._profile.agent_profile(user_id),
            metadata=await self._settings.run_metadata(user_id),
        )

    async def answer(
        self, user_id: UUID, chat_id: UUID, task_id: str, answer: Answer
    ) -> Run[str]:
        """Answer the widget a paused turn of the chat asked, and run the turn on"""
        return await self._ezcareer.resume(
            _AGENT,
            str,
            context_id=f"{user_id}:{chat_id}",
            task_id=task_id,
            answer=answer,
            metadata=await self._settings.run_metadata(user_id),
        )


__all__ = ["AssistantService"]
