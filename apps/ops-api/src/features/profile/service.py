from __future__ import annotations

from hashlib import sha256
from typing import Literal
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import get_settings
from src.core.exceptions import InvalidInput, NotFound
from src.features.profile.enums import ChangeChoice, ChangeKind, EntryKind, ImportSource
from src.features.profile.models import (
    Profile,
    ProfileChange,
    ProfileEntry,
    ProfileImport,
    ProfileSkill,
)
from src.features.profile.repository import ProfileRepository
from src.features.profile.schemas import (
    AgentProfile,
    ChangeAnswers,
    ChangeRead,
    EntryCreate,
    EntryRead,
    EntryWrite,
    ImportedEntry,
    ImportedProfile,
    NetworkingCopy,
    NetworkingRead,
    Preferences,
    ProfileFact,
    ProfileImportRead,
    ProfileRead,
    ProfileUpdate,
    Salary,
    SkillRead,
    SkillWrite,
)
from src.features.profile.sync import (
    ABOUT_FIELDS,
    ENTRY_FIELDS,
    agrees,
    entry_match,
    normalised,
    stored,
)
from src.features.profile.types import ChangeField, FieldValue

_CHANGE: TypeAdapter[ChangeRead] = TypeAdapter(ChangeRead)


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
    """An entry as one fact, a line each for heading, summary, highlights, tools, links;
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
    lines = (
        heading,
        entry.summary,
        *entry.highlights,
        f"Tools: {', '.join(entry.tools)}" if entry.tools else "",
        f"Live at {entry.link}" if entry.link else "",
        f"Code at {entry.code_link}" if entry.code_link else "",
    )
    is_role = entry.kind is EntryKind.ROLE
    return ProfileFact(
        id=f"{entry.kind.value}-{entry.id}",
        text="\n".join(line.strip() for line in lines if line.strip()),
        start=entry.start if is_role else None,
        end=entry.end if is_role else None,
    )


def _skill_fact(skill: ProfileSkill) -> ProfileFact:
    """A skill as one fact, under its group when it has one"""
    return ProfileFact(
        id=f"skill-{skill.id}",
        text=f"{skill.group}: {skill.name}" if skill.group else skill.name,
    )


class ProfileService:
    def __init__(self, session: AsyncSession):
        """Read and write the profile through a repository on the session"""
        self._repository = ProfileRepository(session)

    async def get(self, user_id: UUID) -> ProfileRead:
        """The user's profile, created empty on first read"""
        return _to_read(await self._load(user_id))

    async def update(self, user_id: UUID, patch: ProfileUpdate) -> ProfileRead:
        """Change the fields sent and leave the rest"""
        profile = await self._load(user_id)
        for field, value in patch.model_dump(
            exclude_none=True, exclude={"preferences", "links"}
        ).items():
            setattr(profile, field, value)
        if patch.links is not None:
            profile.links = patch.links
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
        row = await self._repository.owned(ProfileEntry, user_id, entry_id)
        if row is None:
            raise NotFound("No such entry")
        for field, value in entry.model_dump().items():
            setattr(row, field, value)
        return EntryRead.model_validate(row, from_attributes=True)

    async def delete_entry(self, user_id: UUID, entry_id: UUID) -> None:
        """Remove an entry"""
        row = await self._repository.owned(ProfileEntry, user_id, entry_id)
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
        row = await self._repository.owned(ProfileSkill, user_id, skill_id)
        if row is None:
            raise NotFound("No such skill")
        for field, value in skill.model_dump().items():
            setattr(row, field, value)
        return SkillRead.model_validate(row, from_attributes=True)

    async def delete_skill(self, user_id: UUID, skill_id: UUID) -> None:
        """Remove a skill"""
        row = await self._repository.owned(ProfileSkill, user_id, skill_id)
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
            + [_skill_fact(s) for s in skills if not s.archived],
            preferences=_preferences(await self._load(user_id)),
        )

    async def networking_facts(self, user_id: UUID) -> list[ProfileFact]:
        """Every fact the Networking copy is written from: the user's headline,
        summary and location, then every entry and skill, archived ones included"""
        profile = await self._load(user_id)
        about = "\n".join(
            line
            for line in (profile.headline, profile.summary, profile.location)
            if line
        )
        return [
            *([ProfileFact(id="about", text=about)] if about else []),
            *map(_entry_fact, await self._repository.entries(user_id)),
            *map(_skill_fact, await self._repository.skills(user_id)),
        ]

    async def networking(self, user_id: UUID) -> NetworkingRead:
        """The latest Networking copy and the roles it was written for"""
        profile = await self._load(user_id)
        return NetworkingRead(
            aim=profile.networking_aim,
            **(profile.networking or NetworkingCopy()).model_dump(),
        )

    async def keep_networking(
        self, user_id: UUID, aim: str, written: NetworkingCopy, only: str | None
    ) -> NetworkingRead:
        """Keep newly written copy: all of it, or only the headline, summary or
        one fact's description"""
        profile = await self._load(user_id)
        copy = profile.networking or NetworkingCopy()
        match only:
            case None:
                copy = written
            case "headline" | "summary":
                copy = copy.model_copy(update={only: getattr(written, only)})
            case fact:
                copy = copy.model_copy(
                    update={
                        "descriptions": [
                            *(d for d in copy.descriptions if d.fact != fact),
                            *(d for d in written.descriptions if d.fact == fact),
                        ]
                    }
                )
        profile.networking = copy
        profile.networking_aim = aim
        return await self.networking(user_id)

    async def imports(self, user_id: UUID) -> list[ProfileImportRead]:
        """Every import into the profile, the latest first"""
        return [
            ProfileImportRead.model_validate(row, from_attributes=True)
            for row in await self._repository.imports(user_id)
        ]

    async def imported(self, user_id: UUID, content: bytes) -> ProfileImportRead | None:
        """The user's earlier import of this very file, if any"""
        row = await self._repository.imported(user_id, sha256(content).hexdigest())
        return (
            ProfileImportRead.model_validate(row, from_attributes=True) if row else None
        )

    async def changes(self, user_id: UUID) -> list[ChangeRead]:
        """Every change imports left for the user to settle, the oldest first"""
        return [
            _CHANGE.validate_python(change, from_attributes=True)
            for change in await self._repository.changes(user_id)
        ]

    async def _drop(self, changes: list[ProfileChange], change: ProfileChange) -> None:
        """Delete a pending change"""
        changes.remove(change)
        await self._repository.delete(change)

    async def _offer(
        self,
        changes: list[ProfileChange],
        import_id: UUID,
        target: Profile | ProfileEntry,
        field: ChangeField,
        incoming: FieldValue,
    ) -> Literal["filled", "conflict"] | None:
        """Settle one imported value: fill an empty field, drop the field's pending
        change once the import agrees, or keep one pending change with its value"""
        if not incoming:
            return None
        entry_id = target.id if isinstance(target, ProfileEntry) else None
        pending = next(
            (
                c
                for c in changes
                if c.kind is ChangeKind.FIELD
                and c.entry_id == entry_id
                and c.field == field
            ),
            None,
        )
        current = getattr(target, field)
        if agrees(field, current, incoming):
            if pending is not None:
                await self._drop(changes, pending)
            return None
        if not current:
            if pending is not None:
                await self._drop(changes, pending)
            setattr(target, field, stored(field, incoming))
            return "filled"
        if pending is not None:
            pending.import_id = import_id
            pending.current = current
            pending.conflict = stored(field, incoming)
        else:
            changes.append(
                await self._repository.add(
                    ProfileChange(
                        user_id=target.user_id,
                        import_id=import_id,
                        kind=ChangeKind.FIELD,
                        entry_id=entry_id,
                        field=field,
                        current=current,
                        conflict=stored(field, incoming),
                    )
                )
            )
        return "conflict"

    async def _merge(
        self,
        changes: list[ProfileChange],
        import_id: UUID,
        entry: ProfileEntry,
        incoming: ImportedEntry,
    ) -> list[Literal["filled", "conflict"] | None]:
        """Offer each of an imported entry's fields to the entry it is"""
        return [
            await self._offer(
                changes, import_id, entry, field, getattr(incoming, field)
            )
            for field in ENTRY_FIELDS
        ]

    async def _add_entry(self, user_id: UUID, incoming: ImportedEntry) -> ProfileEntry:
        """Store an imported entry as a new one the assistant uses, off the site"""
        return await self._repository.add(
            ProfileEntry(
                user_id=user_id,
                kind=incoming.kind,
                archived=False,
                on_site=False,
                **{
                    field: stored(field, getattr(incoming, field))
                    for field in ENTRY_FIELDS
                },
            )
        )

    async def sync(
        self,
        user_id: UUID,
        source: ImportSource,
        filename: str,
        media_type: str,
        content: bytes,
        imported: ImportedProfile,
    ) -> ProfileImportRead:
        """Add what an import brings that the profile lacks and leave a pending change
        for each value it would overwrite or entry it may be; the same file again
        changes nothing"""
        digest = sha256(content).hexdigest()
        if (earlier := await self._repository.imported(user_id, digest)) is not None:
            return ProfileImportRead.model_validate(earlier, from_attributes=True)
        profile = await self._load(user_id)
        changes = await self._repository.changes(user_id)
        row = await self._repository.add(
            ProfileImport(
                user_id=user_id,
                filename=filename[:255],
                media_type=media_type,
                size=len(content),
                digest=digest,
                source=source,
            )
        )
        outcomes = [
            await self._offer(
                changes, row.id, profile, field, getattr(imported.about, field)
            )
            for field in ABOUT_FIELDS
        ]
        known = {normalised(link.url) for link in profile.links}
        for link in imported.about.links:
            if len(profile.links) < 3 and normalised(link.url) not in known:
                profile.links = [*profile.links, link]
                known.add(normalised(link.url))
                row.added += 1
        unmatched = list(await self._repository.entries(user_id))
        cutoff = get_settings().profile.match_cutoff
        for incoming in imported.entries:
            exact = next(
                (e for e in unmatched if entry_match(e, incoming, cutoff) == "exact"),
                None,
            )
            unsure = next(
                (e for e in unmatched if entry_match(e, incoming, cutoff) == "unsure"),
                None,
            )
            if exact is not None:
                unmatched.remove(exact)
                row.matched += 1
                outcomes += await self._merge(changes, row.id, exact, incoming)
            elif unsure is not None:
                unmatched.remove(unsure)
                row.conflicts += 1
                pending = next(
                    (
                        c
                        for c in changes
                        if c.kind is ChangeKind.MATCH and c.entry_id == unsure.id
                    ),
                    None,
                )
                if pending is not None:
                    pending.import_id = row.id
                    pending.entry = incoming
                else:
                    changes.append(
                        await self._repository.add(
                            ProfileChange(
                                user_id=user_id,
                                import_id=row.id,
                                kind=ChangeKind.MATCH,
                                entry_id=unsure.id,
                                entry=incoming,
                            )
                        )
                    )
            else:
                await self._add_entry(user_id, incoming)
                row.added += 1
        names = {
            skill.name.strip().casefold()
            for skill in await self._repository.skills(user_id)
        }
        for skill in imported.skills:
            if skill.name.strip().casefold() in names:
                row.matched += 1
            else:
                await self._repository.add(
                    ProfileSkill(user_id=user_id, name=skill.name, group=skill.group)
                )
                names.add(skill.name.strip().casefold())
                row.added += 1
        row.added += outcomes.count("filled")
        row.conflicts += outcomes.count("conflict")
        await self._repository.flush()
        return ProfileImportRead.model_validate(row, from_attributes=True)

    async def resolve(self, user_id: UUID, answers: ChangeAnswers) -> list[ChangeRead]:
        """Settle pending changes: keep the current value or take the import's, and
        merge a match into its entry or add it as another"""
        changes = await self._repository.changes(user_id)
        for answer in answers.answers:
            change = next((c for c in changes if c.id == answer.id), None)
            if change is None:
                raise NotFound("No such change")
            target = (
                await self._repository.owned(ProfileEntry, user_id, change.entry_id)
                if change.entry_id
                else await self._load(user_id)
            )
            match change.kind, answer.choice:
                case ChangeKind.FIELD, ChangeChoice.CURRENT:
                    pass
                case ChangeKind.FIELD, ChangeChoice.CONFLICT:
                    if target is not None and change.field:
                        setattr(target, change.field, change.conflict)
                case ChangeKind.MATCH, ChangeChoice.SAME:
                    if isinstance(target, ProfileEntry) and change.entry:
                        await self._merge(
                            changes, change.import_id, target, change.entry
                        )
                case ChangeKind.MATCH, ChangeChoice.DIFFERENT:
                    if change.entry:
                        await self._add_entry(user_id, change.entry)
                case _:
                    raise InvalidInput(
                        "Answer a field with current or conflict,"
                        " and a match with same or different"
                    )
            await self._drop(changes, change)
        return await self.changes(user_id)

    async def _load(self, user_id: UUID) -> Profile:
        """The user's profile row, created empty when missing"""
        return await self._repository.profile(user_id) or await self._repository.create(
            user_id
        )


__all__ = ["ProfileService"]
