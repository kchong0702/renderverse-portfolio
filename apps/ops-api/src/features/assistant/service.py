from __future__ import annotations

from uuid import UUID

from src.features.assistant.schemas import ChatMessage
from src.features.profile import ProfileService
from src.integrations.ezcareer import Answer, EzcareerClient, Run

_AGENT = "career-director"


class AssistantService:
    def __init__(self, profile: ProfileService, ezcareer: EzcareerClient):
        """Keep the profile the agent reads and the harness it runs on"""
        self._profile = profile
        self._ezcareer = ezcareer

    async def send(self, user_id: UUID, message: ChatMessage) -> Run[str]:
        """Start a turn: career-director answers the user's text with their
        profile's facts and preferences"""
        return await self._ezcareer.send(
            _AGENT,
            str,
            context_id=str(user_id),
            text=message.text,
            data=await self._profile.agent_profile(user_id),
        )

    async def answer(self, user_id: UUID, task_id: str, answer: Answer) -> Run[str]:
        """Answer the widget a paused turn asked, and run the turn on"""
        return await self._ezcareer.resume(
            _AGENT, str, context_id=str(user_id), task_id=task_id, answer=answer
        )


__all__ = ["AssistantService"]
