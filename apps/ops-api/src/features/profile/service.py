from __future__ import annotations

from uuid import UUID

from src.core.exceptions import NotFound
from src.features.profile.models import (
    EntryKind,
    Profile,
    ProfileEntry,
    ProfileSkill,
)
from src.features.profile.repository import ProfileRepository
from src.features.profile.schemas import (
    AgentProfile,
    EntryCreate,
    EntryRead,
    EntryWrite,
    Preferences,
    ProfileFact,
    ProfileRead,
    ProfileUpdate,
    Salary,
    SkillRead,
    SkillWrite,
)


def _preferences(profile: Profile) -> Preferences:
    """The preference columns as one Preferences"""
    return Preferences(
        work_modes=profile.work_modes,
        countries=profile.countries,
        authorised_countries=profile.authorised_countries,
        min_salary=Salary(
            amount=profile.min_salary_amount,
            currency=profile.min_salary_currency,
            period=profile.min_salary_period,
        )
        if profile.min_salary_amount is not None
        and profile.min_salary_currency is not None
        and profile.min_salary_period is not None
        else None,
    )


def _to_read(profile: Profile) -> ProfileRead:
    """The profile row as the API returns it"""
    return ProfileRead(
        name=profile.name,
        headline=profile.headline,
        location=profile.location,
        email=profile.email,
        phone=profile.phone,
        links=profile.links,
        summary=profile.summary,
        preferences=_preferences(profile),
    )


def _entry_fact(entry: ProfileEntry) -> ProfileFact:
    """An entry as one fact, its heading then summary and highlights a line each;
    only a role carries its span, as the agents count spans as years of experience"""
    where = ", ".join(part for part in (entry.organisation, entry.location) if part)
    match entry.kind:
        case EntryKind.ROLE:
            heading = f"{entry.title} at {where}" if where else entry.title
        case EntryKind.EDUCATION:
            heading = f"{entry.title}, {where}" if where else entry.title
        case EntryKind.PROJECT:
            heading = f"Project {entry.title}" + (f" for {where}" if where else "")
    start = entry.start[:4] if entry.start else ""
    end = entry.end[:4] if entry.end and entry.end != "present" else entry.end or ""
    years = f"{start} to {end}" if start and end and start != end else start or end
    if years and entry.kind is not EntryKind.ROLE:
        heading = f"{heading} ({years})"
    lines = (heading, entry.summary, *entry.highlights)
    is_role = entry.kind is EntryKind.ROLE
    return ProfileFact(
        id=f"{entry.kind.value}-{entry.id}",
        text="\n".join(line.strip() for line in lines if line.strip()),
        start=entry.start if is_role else None,
        end=entry.end if is_role else None,
    )


class ProfileService:
    def __init__(self, repository: ProfileRepository):
        """Keep the repository every operation reads and writes through"""
        self._repository = repository

    async def get(self, user_id: UUID) -> ProfileRead:
        """The user's profile, created empty on first read"""
        return _to_read(await self._load(user_id))

    async def update(self, user_id: UUID, patch: ProfileUpdate) -> ProfileRead:
        """Change the fields sent and leave the rest"""
        profile = await self._load(user_id)
        for field, value in patch.model_dump(
            exclude_none=True, exclude={"preferences"}
        ).items():
            setattr(profile, field, value)
        if patch.preferences is not None:
            salary = patch.preferences.min_salary
            profile.work_modes = [mode.value for mode in patch.preferences.work_modes]
            profile.countries = patch.preferences.countries
            profile.authorised_countries = patch.preferences.authorised_countries
            profile.min_salary_amount = salary.amount if salary else None
            profile.min_salary_currency = salary.currency if salary else None
            profile.min_salary_period = salary.period if salary else None
        return _to_read(profile)

    async def entries(self, user_id: UUID) -> list[EntryRead]:
        """Every role, education and project, archived ones included"""
        return [
            EntryRead.model_validate(entry, from_attributes=True)
            for entry in await self._repository.entries(user_id)
        ]

    async def add_entry(self, user_id: UUID, entry: EntryCreate) -> EntryRead:
        """Store a new entry"""
        row = await self._repository.add(
            ProfileEntry(user_id=user_id, **entry.model_dump())
        )
        return EntryRead.model_validate(row, from_attributes=True)

    async def replace_entry(
        self, user_id: UUID, entry_id: UUID, entry: EntryWrite
    ) -> EntryRead:
        """Overwrite every field of an entry but its kind"""
        row = await self._repository.entry(user_id, entry_id)
        if row is None:
            raise NotFound("No such entry")
        for field, value in entry.model_dump().items():
            setattr(row, field, value)
        return EntryRead.model_validate(row, from_attributes=True)

    async def delete_entry(self, user_id: UUID, entry_id: UUID) -> None:
        """Remove an entry"""
        row = await self._repository.entry(user_id, entry_id)
        if row is None:
            raise NotFound("No such entry")
        await self._repository.delete(row)

    async def skills(self, user_id: UUID) -> list[SkillRead]:
        """Every skill, archived ones included"""
        return [
            SkillRead.model_validate(skill, from_attributes=True)
            for skill in await self._repository.skills(user_id)
        ]

    async def add_skill(self, user_id: UUID, skill: SkillWrite) -> SkillRead:
        """Store a new skill"""
        row = await self._repository.add(
            ProfileSkill(user_id=user_id, **skill.model_dump())
        )
        return SkillRead.model_validate(row, from_attributes=True)

    async def replace_skill(
        self, user_id: UUID, skill_id: UUID, skill: SkillWrite
    ) -> SkillRead:
        """Overwrite every field of a skill"""
        row = await self._repository.skill(user_id, skill_id)
        if row is None:
            raise NotFound("No such skill")
        for field, value in skill.model_dump().items():
            setattr(row, field, value)
        return SkillRead.model_validate(row, from_attributes=True)

    async def delete_skill(self, user_id: UUID, skill_id: UUID) -> None:
        """Remove a skill"""
        row = await self._repository.skill(user_id, skill_id)
        if row is None:
            raise NotFound("No such skill")
        await self._repository.delete(row)

    async def agent_profile(self, user_id: UUID) -> AgentProfile:
        """The profile as ezcareer-harness's agents take it: unarchived entries
        and skills as facts, and the preferences"""
        entries = await self._repository.entries(user_id)
        skills = await self._repository.skills(user_id)
        return AgentProfile(
            facts=[_entry_fact(e) for e in entries if not e.archived]
            + [
                ProfileFact(
                    id=f"skill-{s.id}",
                    text=f"{s.group}: {s.name}" if s.group else s.name,
                )
                for s in skills
                if not s.archived
            ],
            preferences=_preferences(await self._load(user_id)),
        )

    async def _load(self, user_id: UUID) -> Profile:
        """The user's profile row, created empty when missing"""
        profile = await self._repository.profile(user_id)
        if profile is None:
            profile = await self._repository.add(Profile(user_id=user_id))
        return profile


__all__ = ["ProfileService"]
