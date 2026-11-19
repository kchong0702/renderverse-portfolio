from __future__ import annotations

from collections import Counter
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.db.session import session_scope
from src.features.applications.enums import ApplicationStage
from src.features.applications.repository import ApplicationRepository
from src.features.applications.schemas import ApplicationsAnswer, ApplicationSummary
from src.features.applications.service import ordered_applications
from src.features.settings.repository import SettingsRepository


class ApplicationsRequest(BaseModel):
    execute_tool: Literal["applications"]
    """A paused run asks for the user's applications"""

    company: str | None = None
    """Only applications to a company whose name contains this; every company when
    None"""

    stage: ApplicationStage | None = None
    """Only applications at this stage; every stage when None"""


async def applications(
    factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
    request: ApplicationsRequest,
) -> ApplicationsAnswer:
    """The user's applications to the company asked, counted by stage, and those at
    the stage asked, on a session of its own"""
    async for session in session_scope(factory):
        settings = await SettingsRepository(session).get(user_id)
        timezone = (settings.timezone if settings else None) or "UTC"
        found = [
            read
            for read in await ordered_applications(
                ApplicationRepository(session), user_id, ZoneInfo(timezone)
            )
            if request.company is None
            or request.company.casefold() in read.company.casefold()
        ]
        counts = Counter(read.stage for read in found)
        result = ApplicationsAnswer(
            by_stage={stage: counts[stage] for stage in ApplicationStage},
            applications=[
                ApplicationSummary.model_validate(read, from_attributes=True)
                for read in found
                if request.stage is None or read.stage is request.stage
            ],
            timezone=timezone,
        )
    return result


__all__ = ["ApplicationsRequest", "applications"]
