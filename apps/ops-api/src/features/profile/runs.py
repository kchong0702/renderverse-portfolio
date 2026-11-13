from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.agent_runner import AgentRunner
from src.core.exceptions import InvalidInput, NotFound
from src.features.profile.schemas import (
    NetworkingCopy,
    NetworkingRead,
    NetworkingWrite,
    WriteNetworkingInput,
)
from src.features.profile.service import ProfileService
from src.features.settings import SettingsService


class ProfileRunService:
    def __init__(
        self,
        session: AsyncSession,
        profile: ProfileService,
        settings: SettingsService,
        runner: AgentRunner,
    ):
        """Hold the session, the profile and settings services and the runner"""
        self._session = session
        self._profile = profile
        self._settings = settings
        self._runner = runner

    async def write_networking(
        self, user_id: UUID, request: NetworkingWrite
    ) -> NetworkingRead:
        """Write the Networking copy from every fact, archived ones included, or
        only its headline, summary or one role's or project's description"""
        facts = await self._profile.networking_facts(user_id)
        if request.only not in (None, "headline", "summary"):
            if not request.only.startswith(("role-", "project-")):
                raise InvalidInput(
                    "Only the headline, the summary or a role's or project's"
                    " description can be rewritten"
                )
            if request.only not in {fact.id for fact in facts}:
                raise NotFound("No such fact")
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        written = await self._runner.run(
            user_id,
            "write-networking",
            NetworkingCopy,
            data=WriteNetworkingInput(
                profession=request.profession, facts=facts, only=request.only
            ),
            metadata=metadata,
        )
        return await self._profile.keep_networking(
            user_id, request.profession, written, request.only
        )


__all__ = ["ProfileRunService"]
