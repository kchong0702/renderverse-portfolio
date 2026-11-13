from __future__ import annotations

import hashlib
from base64 import b64encode
from collections.abc import AsyncIterator
from pathlib import Path, PurePosixPath
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.storage import LocalStorage, Storage, UploadTarget
from src.core.config import get_settings
from src.core.exceptions import Conflict, InvalidInput, NotFound
from src.features.portfolio.enums import MediaSlot, MediaType
from src.features.portfolio.models import Asset, PortfolioRelease
from src.features.portfolio.repository import PortfolioRepository
from src.features.portfolio.schemas import (
    About,
    AssetProject,
    AssetRead,
    Change,
    DraftRead,
    ReleaseRead,
    Site,
    SiteProject,
    SiteSkill,
    Snapshot,
    Upload,
)
from src.features.profile import ProfileService
from src.features.profile.enums import EntryKind
from src.features.profile.models import ProfileEntry
from src.features.profile.schemas import EntryRead


def _key(asset: Asset) -> str:
    """The file's public key under its owner's site, which reaches it at /<key>"""
    return f"sites/{asset.user_id}/media/{asset.sha256}{asset.media_type.extension}"


def _private_key(user_id: UUID, sha256: str) -> str:
    """The file's key in private storage, under its owner"""
    return f"{user_id}/{sha256}"


def _media(snapshot: Snapshot) -> set[str]:
    """The public keys of the files a snapshot shows"""
    return {
        url.removeprefix("/")
        for project in snapshot.projects
        for url in (project.image, project.video)
        if url
    }


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
        self._session = session
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
                live.snapshot
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
        await self._repository.lock(user_id)
        live = await self._repository.live(user_id)
        snapshot = await self._snapshot(user_id)
        if live is not None:
            if live.snapshot == snapshot:
                raise Conflict(f"Nothing has changed since release {live.number}")
            live.live = False
            await self._session.flush()
        release = await self._repository.add(
            PortfolioRelease(
                user_id=user_id,
                number=await self._repository.last_number(user_id) + 1,
                snapshot=snapshot,
                live=True,
            )
        )
        await self._write(release)
        return ReleaseRead.model_validate(release, from_attributes=True)

    async def make_live(self, user_id: UUID, release_id: UUID) -> ReleaseRead:
        """Serve an earlier or later release instead of the live one"""
        await self._repository.lock(user_id)
        release = await self._repository.owned(PortfolioRelease, user_id, release_id)
        if release is None:
            raise NotFound("No such release")
        live = await self._repository.live(user_id)
        if live is not None:
            live.live = False
            await self._session.flush()
        release.live = True
        await self._write(release)
        return ReleaseRead.model_validate(release, from_attributes=True)

    def upload_target(self, user_id: UUID, upload: Upload) -> UploadTarget:
        """Where the browser uploads the file, straight to storage"""
        return self._storage.upload_target(
            _private_key(user_id, upload.sha256),
            upload.media_type,
            upload.size,
            b64encode(bytes.fromhex(upload.sha256)).decode(),
        )

    async def receive_upload(
        self,
        user_id: UUID,
        sha256: str,
        media_type: MediaType,
        body: AsyncIterator[bytes],
    ) -> None:
        """Keep a file uploaded to the local storage, checked as R2 checks it"""
        digest, size = hashlib.sha256(), 0
        with self._local().write_private(_private_key(user_id, sha256)) as file:
            async for chunk in body:
                size += len(chunk)
                if size > media_type.max_bytes:
                    raise InvalidInput(media_type.too_large)
                digest.update(chunk)
                file.write(chunk)
            if digest.hexdigest() != sha256:
                raise InvalidInput("The file does not match its SHA-256")

    async def uploaded_file(self, user_id: UUID, sha256: str) -> tuple[Path, MediaType]:
        """Where the local storage keeps one of the user's files, and its type"""
        asset = await self._repository.asset(user_id, sha256)
        path = self._local().private_path(_private_key(user_id, sha256))
        if asset is None or path is None:
            raise NotFound("No such file")
        return path, asset.media_type

    async def add_asset(self, user_id: UUID, upload: Upload) -> AssetRead:
        """Keep an uploaded file; uploading the same file again keeps it once"""
        if (
            await self._storage.size(_private_key(user_id, upload.sha256))
            != upload.size
        ):
            raise Conflict("The file has not been uploaded")
        asset = await self._repository.asset(user_id, upload.sha256)
        if asset is None:
            asset = await self._repository.add(
                Asset(user_id=user_id, **upload.model_dump())
            )
        return self._asset_read(asset, await self._profile.entries(user_id))

    async def assets(self, user_id: UUID) -> list[AssetRead]:
        """The user's files, latest first, with the projects showing each"""
        entries = await self._profile.entries(user_id)
        return [
            self._asset_read(asset, entries)
            for asset in await self._repository.assets(user_id)
        ]

    async def delete_asset(self, user_id: UUID, asset_id: UUID) -> None:
        """Delete a file no project shows; storage keeps it while a release shows it"""
        asset = await self._repository.owned(Asset, user_id, asset_id)
        if asset is None:
            raise NotFound("No such file")
        for entry in await self._profile.entries(user_id):
            if asset.id in (entry.image_id, entry.video_id):
                raise Conflict(f"{entry.title} shows this file")
        await self._repository.delete(asset)
        await self._session.commit()
        if not any(
            _key(asset) in _media(release.snapshot)
            for release in await self._repository.releases(user_id)
        ):
            await self._storage.delete(_private_key(user_id, asset.sha256))

    async def choose_media(
        self, user_id: UUID, project_id: UUID, slot: MediaSlot, asset_id: UUID | None
    ) -> None:
        """Show a file as the project's image or video, or show none"""
        project = await self._repository.owned(ProfileEntry, user_id, project_id)
        if project is None or project.kind is not EntryKind.PROJECT:
            raise NotFound("No such project")
        if asset_id is not None:
            asset = await self._repository.owned(Asset, user_id, asset_id)
            if asset is None or asset.media_type.slot != slot:
                raise InvalidInput(f"No such {slot}")
        setattr(project, f"{slot}_id", asset_id)

    async def _snapshot(self, user_id: UUID) -> Snapshot:
        """The draft: the profile without contact details, every skill, and every
        project on the site, archived or not"""
        urls = {
            asset.id: f"/{_key(asset)}"
            for asset in await self._repository.assets(user_id)
        }
        return Snapshot(
            about=About.model_validate((await self._profile.get(user_id)).model_dump()),
            skills=[
                SiteSkill.model_validate(skill.model_dump())
                for skill in await self._profile.skills(user_id)
            ],
            projects=[
                SiteProject.model_validate(
                    entry.model_dump()
                    | {
                        "image": urls.get(entry.image_id),
                        "video": urls.get(entry.video_id),
                    }
                )
                for entry in await self._profile.entries(user_id)
                if entry.kind is EntryKind.PROJECT and entry.on_site
            ],
        )

    async def _write(self, release: PortfolioRelease) -> None:
        """Copy its files, prune the user's stale ones, then write current.json"""
        snapshot = release.snapshot
        for key in _media(snapshot):
            await self._storage.publish(
                _private_key(release.user_id, PurePosixPath(key).stem), key
            )
        keep = {
            key
            for recent in await self._repository.lately_live(release.user_id)
            for key in _media(recent.snapshot)
        }
        for key in await self._storage.public_keys(f"sites/{release.user_id}/media/"):
            if key not in keep:
                await self._storage.unpublish(key)
        site = Site(
            number=release.number,
            published_at=release.published_at,
            **snapshot.model_dump(),
        )
        await self._storage.put(
            f"sites/{release.user_id}/release/current.json",
            site.model_dump_json().encode(),
            "application/json",
            "max-age=60",
        )

    def _asset_read(self, asset: Asset, entries: list[EntryRead]) -> AssetRead:
        """The file as the API returns it, with the projects showing it"""
        return AssetRead(
            id=asset.id,
            sha256=asset.sha256,
            media_type=asset.media_type,
            size=asset.size,
            filename=asset.filename,
            created_at=asset.created_at,
            url=self._storage.download_url(_private_key(asset.user_id, asset.sha256)),
            projects=[
                AssetProject(id=entry.id, title=entry.title)
                for entry in entries
                if asset.id in (entry.image_id, entry.video_id)
            ],
        )

    def _local(self) -> LocalStorage:
        """The local storage, which takes uploads through ops-api; 404 on R2"""
        if not isinstance(self._storage, LocalStorage):
            raise NotFound("Files are uploaded straight to R2")
        return self._storage


__all__ = ["PortfolioService"]
