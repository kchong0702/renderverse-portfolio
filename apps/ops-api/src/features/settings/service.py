from __future__ import annotations

from collections.abc import Awaitable, Callable
from uuid import UUID

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.job_sources import JobQuery, JobSource
from src.clients.ezcareer import (
    ModelCatalog,
    ModelChoice,
    RunMetadata,
)
from src.core.config import JSearchSettings, get_settings
from src.core.exceptions import InvalidInput
from src.core.providers import Provider
from src.features.connections import JSearchDetails, api_key_connections
from src.features.google import GoogleService
from src.features.settings.models import UserSettings
from src.features.settings.repository import SettingsRepository
from src.features.settings.schemas import (
    Automation,
    Connection,
    Scheduling,
    SearchQuota,
    SettingsRead,
    SettingsUpdate,
)


def _to_read(settings: UserSettings, connections: list[Connection]) -> SettingsRead:
    return SettingsRead(
        automation=Automation(
            tailor_strong_matches=settings.tailor_strong_matches,
            follow_up_reminders=settings.follow_up_reminders,
            suggest_replies=settings.suggest_replies,
            add_interview_invites=settings.add_interview_invites,
            offer_free_slots=settings.offer_free_slots,
        ),
        scheduling=Scheduling(
            work_day_start=settings.work_day_start,
            work_day_end=settings.work_day_end,
            meeting_gap_minutes=settings.meeting_gap_minutes,
            timezone=settings.timezone,
        ),
        ai_model=ModelChoice(family=settings.ai_family, model=settings.ai_model)
        if settings.ai_family is not None and settings.ai_model is not None
        else None,
        connections=connections,
    )


class SettingsService:
    def __init__(
        self,
        session: AsyncSession,
        google: GoogleService,
        jsearch: JSearchSettings,
    ):
        """Read and write the settings through a repository on the session, read the
        user's Google connection, and keep the user's JSearch key through the
        connection service"""
        self._session = session
        """Committed before JSearch checks a key, so no transaction waits on it"""

        self._repository = SettingsRepository(session)
        self._google = google
        self._jsearch = api_key_connections(
            session, Provider.JSEARCH, jsearch.encryption_key, "JSearch"
        )

    async def _connections(self, settings: UserSettings) -> list[Connection]:
        """Google from its stored grant, JSearch from the stored key and its last
        quota; the portfolio site is connected once portfolio.site_url is set"""
        email = await self._google.email(settings.user_id)
        jsearch = await self._jsearch.get(settings.user_id)
        google = (
            Connection(
                id="google",
                status="connected"
                if await self._google.has_scopes(settings.user_id)
                else "needs_reconnect",
                account=email,
            )
            if email is not None
            else Connection(
                id="google",
                status="not_connected" if self._google.configured else "not_configured",
            )
        )
        return [
            google,
            Connection(
                id="jsearch",
                status="connected" if jsearch is not None else "not_connected",
                quota=SearchQuota(
                    remaining=jsearch.details.quota_remaining,
                    limit=jsearch.details.quota_limit,
                )
                if jsearch is not None
                and isinstance(jsearch.details, JSearchDetails)
                and jsearch.details.quota_remaining is not None
                and jsearch.details.quota_limit is not None
                else None,
            ),
            Connection(
                id="portfolio_site",
                status="connected"
                if get_settings().portfolio.site_url
                else "not_connected",
            ),
        ]

    async def get(self, user_id: UUID) -> SettingsRead:
        """The user's settings, created with the defaults on first read"""
        settings = await self._load(user_id)
        return _to_read(settings, await self._connections(settings))

    async def update(
        self,
        user_id: UUID,
        patch: SettingsUpdate,
        models: Callable[[], Awaitable[ModelCatalog]],
    ) -> SettingsRead:
        """Apply the fields sent; a new model must be one models lists"""
        settings = await self._load(user_id)

        for section in (patch.automation, patch.scheduling):
            if section is not None:
                for field, value in section.model_dump(exclude_unset=True).items():
                    setattr(settings, field, value)
        if "ai_model" in patch.model_fields_set:
            choice = patch.ai_model
            if choice is not None:
                catalog = await models()
                if not any(
                    entry.family == choice.family and choice.model in entry.models
                    for entry in catalog.families
                ):
                    raise InvalidInput(
                        f"ezcareer-harness does not offer {choice.model} for {choice.family}"
                    )
            settings.ai_family = choice.family if choice else None
            settings.ai_model = choice.model if choice else None

        if settings.work_day_start >= settings.work_day_end:
            raise InvalidInput("The work day must end after it starts")
        return _to_read(settings, await self._connections(settings))

    async def connect_jsearch(
        self, user_id: UUID, api_key: SecretStr, source: JobSource
    ) -> SettingsRead:
        """Check the key with one search, then store it, encrypted, in place of any
        earlier one, with the quota it reports; InvalidInput when JSearch refuses it"""
        await self._session.commit()
        found = await source.search(
            JobQuery(query="software engineer", max_jobs=10), api_key.get_secret_value()
        )
        await self._jsearch.connect(user_id, api_key.get_secret_value())
        await self._jsearch.record_quota(user_id, found.remaining, found.limit)
        return await self.get(user_id)

    async def disconnect_jsearch(self, user_id: UUID) -> SettingsRead:
        """Forget the user's JSearch key and its quota; a no-op if none is stored"""
        await self._jsearch.disconnect(user_id)
        return await self.get(user_id)

    async def timezone(self, user_id: UUID) -> str | None:
        """The user's IANA time zone; None until they choose one"""
        settings = await self._repository.get(user_id)
        return settings.timezone if settings else None

    async def run_metadata(self, user_id: UUID) -> RunMetadata | None:
        """The user's chosen model for a harness run; None when they chose none"""
        settings = await self._repository.get(user_id)
        model = (
            ModelChoice(family=settings.ai_family, model=settings.ai_model)
            if settings is not None
            and settings.ai_family is not None
            and settings.ai_model is not None
            else None
        )
        if model is None:
            return None
        return RunMetadata(model=model)

    async def _load(self, user_id: UUID) -> UserSettings:
        return await self._repository.get(user_id) or await self._repository.create(
            user_id
        )


__all__ = ["SettingsService"]
