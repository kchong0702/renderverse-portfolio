from __future__ import annotations

from uuid import UUID

from src.core.exceptions import InvalidInput
from src.features.settings.models import UserSettings
from src.features.settings.repository import SettingsRepository
from src.features.settings.schemas import (
    Automation,
    Connection,
    JobAgent,
    Scheduling,
    SettingsRead,
    SettingsUpdate,
)

_JOB_AGENT_COLUMNS = {
    "query": "job_query",
    "location": "job_location",
    "run_at": "job_agent_run_at",
    "min_score": "job_min_score",
}


def _connections() -> list[Connection]:
    """Every connection stays unconnected until its integration lands"""
    return [
        Connection(id="google", status="not_connected"),
        Connection(id="jsearch", status="not_connected"),
        Connection(id="portfolio_site", status="not_connected"),
    ]


def _to_read(settings: UserSettings) -> SettingsRead:
    return SettingsRead(
        job_agent=JobAgent(
            query=settings.job_query,
            location=settings.job_location,
            run_at=settings.job_agent_run_at,
            min_score=settings.job_min_score,
        ),
        automation=Automation(
            tailor_strong_matches=settings.tailor_strong_matches,
            follow_up_reminders=settings.follow_up_reminders,
            suggest_replies=settings.suggest_replies,
        ),
        scheduling=Scheduling(
            work_day_start=settings.work_day_start,
            work_day_end=settings.work_day_end,
            meeting_gap_minutes=settings.meeting_gap_minutes,
        ),
        ai_provider=settings.ai_provider,  # type: ignore[arg-type]
        connections=_connections(),
    )


class SettingsService:
    def __init__(self, repository: SettingsRepository):
        self._repository = repository

    async def get(self, user_id: UUID) -> SettingsRead:
        return _to_read(await self._load(user_id))

    async def update(self, user_id: UUID, patch: SettingsUpdate) -> SettingsRead:
        settings = await self._load(user_id)

        if patch.job_agent is not None:
            for field, value in patch.job_agent.model_dump(exclude_unset=True).items():
                setattr(settings, _JOB_AGENT_COLUMNS[field], value)
        for section in (patch.automation, patch.scheduling):
            if section is not None:
                for field, value in section.model_dump(exclude_unset=True).items():
                    setattr(settings, field, value)
        if patch.ai_provider is not None:
            settings.ai_provider = patch.ai_provider

        if settings.work_day_start >= settings.work_day_end:
            raise InvalidInput("The work day must end after it starts")
        return _to_read(settings)

    async def _load(self, user_id: UUID) -> UserSettings:
        settings = await self._repository.get(user_id)
        if settings is None:
            settings = await self._repository.add(UserSettings(user_id=user_id))
        return settings


__all__ = ["SettingsService"]
