from __future__ import annotations

from typing import NamedTuple
from uuid import UUID

from document_schema import ResumeDocument
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.ezcareer import DataRequest
from src.core.exceptions import NotFound
from src.features.assistant.schemas import (
    AboutEdit,
    ApprovalRow,
    EntryEdit,
    NewEntry,
    NewLink,
    NewSkill,
    ProfileApproval,
    ProfileEdit,
    ProfileSyncPreview,
    ProfileSyncRequest,
    ProfileUpdated,
    ProfileUpdateRequest,
    UpdateProfileArgs,
)
from src.features.documents import DocumentService
from src.features.documents.schemas import DocumentAnswer, FetchError
from src.features.profile import ImportSource, ProfileService, resume_profile
from src.features.profile.schemas import (
    ChangeRead,
    EntryCreate,
    EntryRead,
    EntryWrite,
    FieldChangeRead,
    ImportedEntry,
    MatchChangeRead,
    ProfileLink,
    ProfileRead,
    ProfileUpdate,
    SkillRead,
    SkillWrite,
)
from src.features.profile.sync import ABOUT_FIELDS, ENTRY_FIELDS, stored


class _Snapshot(NamedTuple):
    profile: ProfileRead
    """The user's details"""

    entries: list[EntryRead]
    """Every role, education and project"""

    skills: list[SkillRead]
    """Every skill"""


async def _snapshot(service: ProfileService, user_id: UUID) -> _Snapshot:
    """The profile as it stands in the service's session"""
    return _Snapshot(
        await service.get(user_id),
        await service.entries(user_id),
        await service.skills(user_id),
    )


def _fact(entry: EntryRead) -> str:
    """The entry's fact id, such as role-<uuid>"""
    return f"{entry.kind.value}-{entry.id}"


def _synced(
    before: _Snapshot, after: _Snapshot, pending: list[ChangeRead]
) -> list[ProfileEdit]:
    """The edits that turn before into after, then each pending change as the edit
    that takes the import's side"""
    earlier = {entry.id: entry for entry in before.entries}
    known = {skill.id for skill in before.skills}
    edits: list[ProfileEdit] = [
        AboutEdit(kind="about", field=field, value=getattr(after.profile, field))
        for field in ABOUT_FIELDS
        if getattr(after.profile, field) != getattr(before.profile, field)
    ]
    edits += [
        NewLink(kind="new_link", label=link.label, url=link.url)
        for link in after.profile.links[len(before.profile.links) :]
    ]
    for entry in after.entries:
        if entry.id not in earlier:
            edits.append(
                NewEntry(
                    kind="new_entry",
                    entry=ImportedEntry.model_validate(entry.model_dump()),
                )
            )
        else:
            edits += [
                EntryEdit(
                    kind="entry",
                    fact=_fact(entry),
                    field=field,
                    value=getattr(entry, field),
                )
                for field in ENTRY_FIELDS
                if getattr(entry, field) != getattr(earlier[entry.id], field)
            ]
    edits += [
        NewSkill(kind="new_skill", name=skill.name, group=skill.group)
        for skill in after.skills
        if skill.id not in known
    ]
    for change in pending:
        match change:
            case FieldChangeRead(entry_id=None):
                edits.append(
                    AboutEdit(kind="about", field=change.field, value=change.conflict)
                )
            case FieldChangeRead(entry_id=entry_id):
                edits.append(
                    EntryEdit(
                        kind="entry",
                        fact=_fact(earlier[entry_id]),
                        field=change.field,
                        value=change.conflict,
                    )
                )
            case MatchChangeRead(entry=entry):
                edits.append(NewEntry(kind="new_entry", entry=entry))
    return edits


async def _apply(
    service: ProfileService, user_id: UUID, edits: list[ProfileEdit]
) -> list[ApprovalRow]:
    """Make the edits through the profile service, each beside the value it replaces;
    NotFound for an entry the user doesn't have, ValidationError for a value the
    profile can't keep"""
    profile = await service.get(user_id)
    entries = {_fact(entry): entry for entry in await service.entries(user_id)}
    rows: list[ApprovalRow] = []
    for edit in edits:
        match edit:
            case AboutEdit(field=field, value=value):
                rows.append(
                    ApprovalRow(edit=edit, entry=None, current=getattr(profile, field))
                )
                profile = await service.update(
                    user_id, ProfileUpdate.model_validate({field: value})
                )
            case EntryEdit(fact=fact, field=field, value=value):
                if (entry := entries.get(fact)) is None:
                    raise NotFound(f"No such entry {fact}")
                rows.append(
                    ApprovalRow(
                        edit=edit,
                        entry=entry.organisation or entry.title,
                        current=getattr(entry, field),
                    )
                )
                entries[fact] = await service.replace_entry(
                    user_id,
                    entry.id,
                    EntryWrite.model_validate(
                        {**entry.model_dump(), field: stored(field, value)}
                    ),
                )
            case NewLink(label=label, url=url):
                rows.append(ApprovalRow(edit=edit, entry=None, current=None))
                profile = await service.update(
                    user_id,
                    ProfileUpdate(
                        links=[*profile.links, ProfileLink(label=label, url=url)]
                    ),
                )
            case NewEntry(entry=entry):
                rows.append(ApprovalRow(edit=edit, entry=None, current=None))
                await service.add_entry(
                    user_id,
                    EntryCreate(
                        kind=entry.kind,
                        **{
                            field: stored(field, getattr(entry, field))
                            for field in ENTRY_FIELDS
                        },
                    ),
                )
            case NewSkill(name=name, group=group):
                rows.append(ApprovalRow(edit=edit, entry=None, current=None))
                await service.add_skill(user_id, SkillWrite(name=name, group=group))
    return rows


class ProfileEdits:
    def __init__(
        self, factory: async_sessionmaker[AsyncSession], documents: DocumentService
    ):
        """Preview and make career-director's changes to the profile on sessions of
        their own, reading résumés through the documents service"""
        self._factory = factory
        self._documents = documents

    async def _preview(self, user_id: UUID, document_id: UUID) -> ProfileSyncPreview:
        """What syncing one of the user's résumés or CVs into the profile would
        change, from a real sync that is rolled back; NotFound for any other document"""
        answer = await self._documents.answer_data_request(
            user_id, DataRequest(fetch="document", id=str(document_id))
        )
        if not isinstance(answer, DocumentAnswer) or not isinstance(
            answer.document, ResumeDocument
        ):
            raise NotFound("No such résumé or CV")
        async with self._factory() as session:
            service = ProfileService(session)
            before = await _snapshot(service, user_id)
            row = await service.sync(
                user_id,
                ImportSource.DOCUMENTS,
                "",
                "application/json",
                answer.document.model_dump_json().encode(),
                resume_profile(answer.document.content),
            )
            after = await _snapshot(service, user_id)
            pending = [
                c for c in await service.changes(user_id) if c.import_id == row.id
            ]
            await session.rollback()
        return ProfileSyncPreview(edits=_synced(before, after, pending))

    async def answer_data_request(
        self, user_id: UUID, request: DataRequest
    ) -> ProfileSyncPreview | ProfileUpdated | FetchError:
        """Answer a paused run's request to preview a sync, or to save approved
        changes all or none; FetchError says why nothing came of it"""
        try:
            match TypeAdapter(
                ProfileSyncRequest | ProfileUpdateRequest
            ).validate_python(request.model_dump()):
                case ProfileSyncRequest(document_id=document_id):
                    return await self._preview(user_id, document_id)
                case ProfileUpdateRequest(edits=edits):
                    async with self._factory() as session, session.begin():
                        await _apply(ProfileService(session), user_id, edits)
                    return ProfileUpdated(saved=len(edits))
        except (ValidationError, NotFound) as error:
            return FetchError(error=str(error))

    async def approval(
        self, user_id: UUID, task_id: str, args: UpdateProfileArgs
    ) -> ProfileApproval:
        """The card asking the user to approve the changes, beside each field's value
        in the database, found by making them on a session that is rolled back;
        NotFound or ValidationError when they can't be made"""
        async with self._factory() as session:
            rows = await _apply(ProfileService(session), user_id, args.edits)
            await session.rollback()
        return ProfileApproval(task_id=task_id, source=args.source, rows=rows)


__all__ = ["ProfileEdits"]
