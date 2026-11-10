from __future__ import annotations

from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.ezcareer import (
    EzcareerClient,
    JSearchMetadata,
    ModelCatalog,
    ModelChoice,
    RunMetadata,
)
from src.core.config import JSearchSettings
from src.core.exceptions import Conflict, InvalidInput, ServiceUnavailable
from src.features.google import GoogleService
from src.features.settings.models import UserSettings
from src.features.settings.repository import SettingsRepository
from src.features.settings.schemas import (
    Automation,
    Connection,
    JobAgent,
    Scheduling,
    SearchQuota,
    SettingsRead,
    SettingsUpdate,
)

_JOB_AGENT_COLUMNS = {
    "query": "job_query",
    "location": "job_location",
    "run_at": "job_agent_run_at",
    "min_score": "job_min_score",
}


def _to_read(settings: UserSettings, connections: list[Connection]) -> SettingsRead:
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
            add_interview_invites=settings.add_interview_invites,
            offer_free_slots=settings.offer_free_slots,
        ),
        scheduling=Scheduling(
            work_day_start=settings.work_day_start,
            work_day_end=settings.work_day_end,
            meeting_gap_minutes=settings.meeting_gap_minutes,
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
        ezcareer: EzcareerClient,
        google: GoogleService,
        jsearch: JSearchSettings,
    ):
        """Read and write the settings through a repository on the session, list the
        models ezcareer-harness serves, read the user's Google connection, and keep
        the key that encrypts JSearch keys"""
        self._repository = SettingsRepository(session)
        self._ezcareer = ezcareer
        self._google = google
        self._jsearch = jsearch

    def _fernet(self) -> Fernet:
        """The cipher for JSearch keys; ServiceUnavailable until the server has one"""
        if not self._jsearch.encryption_key.get_secret_value():
            raise ServiceUnavailable(
                "JSearch keys are not set up on the server: set "
                "OPS_API_JSEARCH__ENCRYPTION_KEY"
            )
        return Fernet(self._jsearch.encryption_key.get_secret_value())

    async def _connections(self, settings: UserSettings) -> list[Connection]:
        """Google from its stored grant, JSearch from the stored key and its last
        quota; the portfolio site waits for its integration"""
        email = await self._google.email(settings.user_id)
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
                status="connected"
                if settings.jsearch_ciphertext is not None
                else "not_connected",
                quota=SearchQuota(
                    remaining=settings.jsearch_quota_remaining,
                    limit=settings.jsearch_quota_limit,
                )
                if settings.jsearch_quota_remaining is not None
                and settings.jsearch_quota_limit is not None
                else None,
            ),
            Connection(id="portfolio_site", status="not_connected"),
        ]

    async def get(self, user_id: UUID) -> SettingsRead:
        """The user's settings, created with the defaults on first read"""
        settings = await self._load(user_id)
        return _to_read(settings, await self._connections(settings))

    async def update(self, user_id: UUID, patch: SettingsUpdate) -> SettingsRead:
        """Apply the fields sent; a new model must be one ezcareer-harness offers"""
        settings = await self._load(user_id)

        if patch.job_agent is not None:
            for field, value in patch.job_agent.model_dump(exclude_unset=True).items():
                setattr(settings, _JOB_AGENT_COLUMNS[field], value)
        for section in (patch.automation, patch.scheduling):
            if section is not None:
                for field, value in section.model_dump(exclude_unset=True).items():
                    setattr(settings, field, value)
        if patch.ai_model is not None:
            choice = patch.ai_model
            catalog = await self._ezcareer.models()
            if not any(
                entry.family == choice.family and choice.model in entry.models
                for entry in catalog.families
            ):
                raise InvalidInput(
                    f"ezcareer-harness does not offer {choice.model} for {choice.family}"
                )
            settings.ai_family = choice.family
            settings.ai_model = choice.model

        if settings.work_day_start >= settings.work_day_end:
            raise InvalidInput("The work day must end after it starts")
        return _to_read(settings, await self._connections(settings))

    async def models(self) -> ModelCatalog:
        """The models a user can pick from, as ezcareer-harness lists them"""
        return await self._ezcareer.models()

    async def connect_jsearch(self, user_id: UUID, api_key: SecretStr) -> SettingsRead:
        """Store the user's JSearch key, encrypted, in place of any earlier one, whose
        quota no longer applies"""
        settings = await self._load(user_id)
        settings.jsearch_ciphertext = self._fernet().encrypt(
            api_key.get_secret_value().encode()
        )
        settings.jsearch_quota_remaining = None
        settings.jsearch_quota_limit = None
        return _to_read(settings, await self._connections(settings))

    async def disconnect_jsearch(self, user_id: UUID) -> SettingsRead:
        """Forget the user's JSearch key and its quota; a no-op if none is stored"""
        settings = await self._load(user_id)
        settings.jsearch_ciphertext = None
        settings.jsearch_quota_remaining = None
        settings.jsearch_quota_limit = None
        return _to_read(settings, await self._connections(settings))

    async def record_quota(self, user_id: UUID, quota: SearchQuota | None) -> None:
        """Keep the quota a find run read on the user's JSearch key; a run on the
        server's key leaves it"""
        settings = await self._load(user_id)
        if settings.jsearch_ciphertext is not None:
            settings.jsearch_quota_remaining = quota.remaining if quota else None
            settings.jsearch_quota_limit = quota.limit if quota else None

    async def run_metadata(self, user_id: UUID) -> RunMetadata | None:
        """The user's chosen model and JSearch key for a harness run; None when they
        set neither; Conflict when the stored key can no longer be read"""
        settings = await self._repository.get(user_id)
        if settings is None:
            return None
        try:
            jsearch = (
                JSearchMetadata(
                    api_key=self._fernet().decrypt(settings.jsearch_ciphertext).decode()
                )
                if settings.jsearch_ciphertext is not None
                else None
            )
        except InvalidToken as error:
            raise Conflict(
                "Ops can no longer read your JSearch key; change it in Settings"
            ) from error
        model = (
            ModelChoice(family=settings.ai_family, model=settings.ai_model)
            if settings.ai_family is not None and settings.ai_model is not None
            else None
        )
        if model is None and jsearch is None:
            return None
        return RunMetadata(model=model, jsearch=jsearch)

    async def _load(self, user_id: UUID) -> UserSettings:
        return await self._repository.get(user_id) or await self._repository.create(
            user_id
        )


__all__ = ["SettingsService"]
