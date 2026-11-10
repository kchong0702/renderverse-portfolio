from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.storage import Storage
from src.core.config import get_settings
from src.core.exceptions import Conflict, NotFound
from src.features.portfolio.models import PortfolioRelease
from src.features.portfolio.repository import PortfolioRepository
from src.features.portfolio.schemas import (
    About,
    Change,
    DraftRead,
    ReleaseRead,
    Site,
    SiteProject,
    SiteSkill,
    Snapshot,
)
from src.features.profile import ProfileService
from src.features.profile.enums import EntryKind


def _changes(draft: Snapshot, live: Snapshot) -> list[Change]:
    """Every part of the draft that differs from the live snapshot, by item id"""
    changes = (
        [Change(kind="about", id=None, name=draft.about.name, change="changed")]
        if draft.about != live.about
        else []
    )
    for kind, label, now, then in (
        ("skill", "name", draft.skills, live.skills),
        ("project", "title", draft.projects, live.projects),
    ):
        before = {item.id: item for item in then}
        after = {item.id for item in now}
        changes += [
            Change(
                kind=kind,
                id=item.id,
                name=getattr(item, label),
                change="changed" if item.id in before else "added",
            )
            for item in now
            if before.get(item.id) != item
        ] + [
            Change(kind=kind, id=item.id, name=getattr(item, label), change="removed")
            for item in then
            if item.id not in after
        ]
    return changes


class PortfolioService:
    def __init__(self, session: AsyncSession, storage: Storage):
        """Keep releases through a repository on the session, read the draft from
        the profile, and write the live release to storage"""
        self._repository = PortfolioRepository(session)
        self._profile = ProfileService(session)
        self._storage = storage

    async def releases(self, user_id: UUID) -> list[ReleaseRead]:
        """Every release, latest first"""
        return [
            ReleaseRead.model_validate(release, from_attributes=True)
            for release in await self._repository.releases(user_id)
        ]

    async def draft(self, user_id: UUID) -> DraftRead:
        """What publishing now would change, and the number it would take"""
        live = await self._repository.live(user_id)
        return DraftRead(
            site_url=get_settings().portfolio.site_url or None,
            number=await self._repository.last_number(user_id) + 1,
            changes=_changes(
                await self._snapshot(user_id),
                Snapshot.model_validate(live.snapshot)
                if live
                else Snapshot(
                    about=About(
                        name="", headline="", summary="", location="", links=[]
                    ),
                    skills=[],
                    projects=[],
                ),
            ),
        )

    async def publish(self, user_id: UUID) -> ReleaseRead:
        """Store the draft as the next release and make it live"""
        live = await self._repository.live(user_id)
        snapshot = await self._snapshot(user_id)
        if live is not None:
            if Snapshot.model_validate(live.snapshot) == snapshot:
                raise Conflict(f"Nothing has changed since release {live.number}")
            live.live = False
        release = await self._repository.add(
            PortfolioRelease(
                user_id=user_id,
                number=await self._repository.last_number(user_id) + 1,
                snapshot=snapshot.model_dump(mode="json"),
                live=True,
            )
        )
        await self._write(release)
        return ReleaseRead.model_validate(release, from_attributes=True)

    async def make_live(self, user_id: UUID, release_id: UUID) -> ReleaseRead:
        """Serve an earlier or later release instead of the live one"""
        release = await self._repository.owned(PortfolioRelease, user_id, release_id)
        if release is None:
            raise NotFound("No such release")
        live = await self._repository.live(user_id)
        if live is not None:
            live.live = False
        release.live = True
        await self._write(release)
        return ReleaseRead.model_validate(release, from_attributes=True)

    async def _snapshot(self, user_id: UUID) -> Snapshot:
        """The draft: the profile without contact details, unarchived skills, and
        unarchived projects that are on the site"""
        return Snapshot(
            about=About.model_validate((await self._profile.get(user_id)).model_dump()),
            skills=[
                SiteSkill.model_validate(skill.model_dump())
                for skill in await self._profile.skills(user_id)
                if not skill.archived
            ],
            projects=[
                SiteProject.model_validate(entry.model_dump())
                for entry in await self._profile.entries(user_id)
                if entry.kind is EntryKind.PROJECT
                and entry.on_site
                and not entry.archived
            ],
        )

    async def _write(self, release: PortfolioRelease) -> None:
        """Write the release as the site's release/current.json; a failure raises,
        so the request's changes roll back"""
        site = Site(
            number=release.number,
            published_at=release.published_at,
            **Snapshot.model_validate(release.snapshot).model_dump(),
        )
        await self._storage.put(
            f"sites/{release.user_id}/release/current.json",
            site.model_dump_json().encode(),
            "application/json",
            "max-age=60",
        )


__all__ = ["PortfolioService"]
