from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.features.preferences.models import JobPreferences
from src.features.preferences.repository import PreferencesRepository
from src.features.preferences.schemas import (
    PreferencesRead,
    PreferencesUpdate,
    Salary,
)


def _to_read(preferences: JobPreferences) -> PreferencesRead:
    """The preferences row as the API returns it"""
    return PreferencesRead(
        target_roles=preferences.target_roles,
        location=preferences.location,
        countries=preferences.countries,
        visa_free_countries=preferences.visa_free_countries,
        work_modes=preferences.work_modes,
        min_salary=Salary(
            amount=preferences.min_salary_amount,
            currency=preferences.min_salary_currency,
            period=preferences.min_salary_period,
        )
        if preferences.min_salary_amount is not None
        and preferences.min_salary_currency is not None
        and preferences.min_salary_period is not None
        else None,
        min_score=preferences.min_score,
        run_at=preferences.run_at,
    )


class PreferencesService:
    def __init__(self, session: AsyncSession):
        """Read and write job preferences through a repository on the session"""
        self._repository = PreferencesRepository(session)

    async def _load(self, user_id: UUID) -> JobPreferences:
        """The user's preferences row, created with the defaults when missing"""
        return await self._repository.get(user_id) or await self._repository.create(
            user_id
        )

    async def get(self, user_id: UUID) -> PreferencesRead:
        """The user's job preferences, created with the defaults on first read"""
        return _to_read(await self._load(user_id))

    async def update(self, user_id: UUID, patch: PreferencesUpdate) -> PreferencesRead:
        """Change the fields sent and leave the rest; a null min_salary clears it"""
        preferences = await self._load(user_id)
        for field, value in patch.model_dump(
            exclude_none=True, exclude={"min_salary"}
        ).items():
            setattr(preferences, field, value)
        if "min_salary" in patch.model_fields_set:
            salary = patch.min_salary
            preferences.min_salary_amount = salary.amount if salary else None
            preferences.min_salary_currency = salary.currency if salary else None
            preferences.min_salary_period = salary.period if salary else None
        return _to_read(preferences)


__all__ = ["PreferencesService"]
