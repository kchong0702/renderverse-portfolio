from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from document_schema import (
    AnyDocument,
    AnyEdit,
    Changeset,
    ChangesetStatus,
    DocumentKind,
    TemplateSpec,
    apply_edits,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.artifact import ArtifactClient, Render
from src.core.config import DocumentsSettings
from src.core.exceptions import Conflict, InvalidInput, NotFound
from src.features.documents.models import (
    Document,
    DocumentChangeset,
    DocumentImport,
    DocumentVersion,
)
from src.features.documents.repository import DocumentRepository
from src.features.documents.schemas import (
    ChangesetDecision,
    ChangesetRead,
    DocumentCreate,
    DocumentEdits,
    DocumentRead,
    DocumentSummary,
    DocumentUpdate,
    ImportRead,
    VersionCreate,
    VersionRead,
)


def _pending(changesets: Sequence[DocumentChangeset]) -> int:
    """How many of these changesets wait for the user's answer"""
    return sum(row.changeset.status is ChangesetStatus.PENDING for row in changesets)


def _waiting(changesets: Sequence[DocumentChangeset]) -> DocumentChangeset | None:
    """The changeset still waiting for the user's answer, if any"""
    return next(
        (row for row in changesets if row.changeset.status is ChangesetStatus.PENDING),
        None,
    )


def _applied(body: AnyDocument, edits: Sequence[AnyEdit]) -> AnyDocument | None:
    """The body with the edits applied; None when they no longer fit it"""
    try:
        return apply_edits(body, edits)
    except ValueError:
        return None


def _summary(document: Document, pending_changesets: int) -> DocumentSummary:
    """The document as the list shows it"""
    return DocumentSummary(
        id=document.id,
        kind=document.kind,
        title=document.title,
        master=document.master,
        pending_changesets=pending_changesets,
        updated_at=document.updated_at,
    )


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        artifact: ArtifactClient,
        limits: DocumentsSettings,
    ):
        """Read and write documents through a repository on the session, render them
        with artifact-service, and keep at most limits' documents of each kind"""
        self._repository = DocumentRepository(session)
        self._artifact = artifact
        self._limits = limits

    async def _make_room(self, user_id: UUID, kind: DocumentKind) -> None:
        """Conflict when the user already keeps the most documents of this kind"""
        kept = sum(d.kind is kind for d in await self._repository.documents(user_id))
        if kept >= self._limits.max_per_kind:
            raise Conflict(
                f"You already keep {kept} {kind.value.replace('_', ' ')} documents."
                " Delete one to add another."
            )

    async def documents(self, user_id: UUID) -> list[DocumentSummary]:
        """Every résumé, CV and cover letter, with its count of edits to review"""
        documents = await self._repository.documents(user_id)
        changesets = await self._repository.changesets([d.id for d in documents])
        return [
            _summary(d, _pending([c for c in changesets if c.document_id == d.id]))
            for d in documents
        ]

    async def get(self, user_id: UUID, document_id: UUID) -> DocumentRead:
        """One document with its current draft"""
        return await self._read(await self._load(user_id, document_id))

    async def create(self, user_id: UUID, create: DocumentCreate) -> DocumentRead:
        """Store a new document and keep its first draft as version 1; Conflict when
        the user keeps the most of its kind already"""
        await self._make_room(user_id, create.body.kind)
        document = await self._repository.add(
            Document(
                user_id=user_id,
                kind=create.body.kind,
                title=create.title,
                body=create.body,
            )
        )
        await self._keep(document, "Created")
        return await self._read(document)

    async def update(
        self, user_id: UUID, document_id: UUID, patch: DocumentUpdate
    ) -> DocumentRead:
        """Rename a document"""
        document = await self._load(user_id, document_id)
        if patch.title is not None:
            document.title = patch.title
        return await self._read(document)

    async def edit(
        self, user_id: UUID, document_id: UUID, edits: DocumentEdits
    ) -> DocumentRead:
        """Make the user's own edits to the current draft"""
        document = await self._load(user_id, document_id)
        try:
            document.body = apply_edits(document.body, edits.edits)
        except ValueError as error:
            raise InvalidInput(str(error)) from error
        return await self._read(document)

    async def set_master(self, user_id: UUID, document_id: UUID) -> DocumentRead:
        """Make a document the master of its kind, in place of any other"""
        document = await self._load(user_id, document_id)
        await self._repository.clear_master(user_id, document.kind)
        document.master = True
        return await self._read(document)

    async def delete(self, user_id: UUID, document_id: UUID) -> None:
        """Remove a document with its versions and changesets"""
        await self._repository.delete(await self._load(user_id, document_id))

    async def templates(self, kind: DocumentKind) -> list[TemplateSpec]:
        """The templates a document of this kind can be printed with"""
        return await self._artifact.templates(kind)

    async def render(self, user_id: UUID, document_id: UUID) -> Render:
        """The current draft printed as a PDF, with how its pages came out"""
        return await self._artifact.render(
            (await self._load(user_id, document_id)).body
        )

    async def versions(self, user_id: UUID, document_id: UUID) -> list[VersionRead]:
        """Every kept version of a document, the latest first"""
        document = await self._load(user_id, document_id)
        return [
            VersionRead.model_validate(version, from_attributes=True)
            for version in await self._repository.versions(document.id)
        ]

    async def keep_version(
        self, user_id: UUID, document_id: UUID, create: VersionCreate
    ) -> VersionRead:
        """Keep the current draft as the next version"""
        document = await self._load(user_id, document_id)
        version = await self._keep(document, create.label)
        return VersionRead.model_validate(version, from_attributes=True)

    async def restore(
        self, user_id: UUID, document_id: UUID, version_id: UUID
    ) -> DocumentRead:
        """Keep the current draft as a version, then put a kept version back as the
        draft"""
        document = await self._load(user_id, document_id)
        version = await self._repository.version(document.id, version_id)
        if version is None:
            raise NotFound("No such version")
        await self._keep(document, f"Before restoring version {version.number}")
        document.body = version.body
        return await self._read(document)

    async def changesets(self, user_id: UUID, document_id: UUID) -> list[ChangesetRead]:
        """Every changeset proposed for a document, the latest first"""
        document = await self._load(user_id, document_id)
        return [
            ChangesetRead.model_validate(row, from_attributes=True)
            for row in await self._repository.changesets([document.id])
        ]

    async def propose(
        self, user_id: UUID, document_id: UUID, changeset: Changeset
    ) -> ChangesetRead:
        """Store an agent's changeset for the user to accept or reject, adding its edits
        to the one still pending; the edits must apply to the current draft"""
        document = await self._load(user_id, document_id)
        if changeset.status is not ChangesetStatus.PENDING:
            raise InvalidInput("A new changeset must be pending")
        pending = _waiting(await self._repository.changesets([document.id]))
        edits = [*(pending.changeset.edits if pending else []), *changeset.edits]
        try:
            apply_edits(document.body, edits)
        except ValueError as error:
            raise InvalidInput(str(error)) from error
        if pending:
            pending.changeset = pending.changeset.model_copy(
                update={"edits": edits, "reason": changeset.reason}
            )
            await self._repository.flush()
            return ChangesetRead.model_validate(pending, from_attributes=True)
        row = await self._repository.add(
            DocumentChangeset(
                user_id=user_id,
                document_id=document.id,
                changeset=changeset,
            )
        )
        return ChangesetRead.model_validate(row, from_attributes=True)

    async def undo_edit(
        self, user_id: UUID, document_id: UUID, changeset_id: UUID, index: int
    ) -> ChangesetRead:
        """Take one edit out of a pending changeset, closing it as rejected when none
        is left; Conflict when the edits left no longer fit the draft"""
        document = await self._load(user_id, document_id)
        row = await self._repository.changeset(document.id, changeset_id)
        if row is None or not 0 <= index < len(row.changeset.edits):
            raise NotFound("No such edit")
        if row.changeset.status is not ChangesetStatus.PENDING:
            raise Conflict("This changeset is already answered")
        edits = [e for i, e in enumerate(row.changeset.edits) if i != index]
        if not edits:
            row.changeset = row.changeset.model_copy(
                update={"status": ChangesetStatus.REJECTED}
            )
        else:
            try:
                apply_edits(document.body, edits)
            except ValueError as error:
                raise Conflict(
                    f"The other edits need this one to fit the document: {error}"
                ) from error
            row.changeset = row.changeset.model_copy(update={"edits": edits})
        return ChangesetRead.model_validate(row, from_attributes=True)

    async def decide(
        self,
        user_id: UUID,
        document_id: UUID,
        changeset_id: UUID,
        decision: ChangesetDecision,
    ) -> ChangesetRead:
        """Accept a changeset, applying every edit to the draft and keeping a version,
        or reject it; Conflict once it is answered or when its edits no longer fit"""
        document = await self._load(user_id, document_id)
        row = await self._repository.changeset(document.id, changeset_id)
        if row is None:
            raise NotFound("No such changeset")
        if row.changeset.status is decision.status:
            return ChangesetRead.model_validate(row, from_attributes=True)
        if row.changeset.status is not ChangesetStatus.PENDING:
            raise Conflict("This changeset is already answered")
        if decision.status is ChangesetStatus.ACCEPTED:
            try:
                edited = apply_edits(document.body, row.changeset.edits)
            except ValueError as error:
                raise Conflict(
                    f"These edits no longer fit the document: {error}"
                ) from error
            await self._keep(document, f"Before {row.changeset.agent}'s edits")
            document.body = edited
        row.changeset = row.changeset.model_copy(update={"status": decision.status})
        return ChangesetRead.model_validate(row, from_attributes=True)

    async def imports(self, user_id: UUID) -> list[ImportRead]:
        """Every uploaded résumé file, the latest first"""
        return [
            ImportRead.model_validate(row, from_attributes=True)
            for row in await self._repository.imports(user_id)
        ]

    async def start_import(
        self, user_id: UUID, filename: str, media_type: str, content: bytes
    ) -> ImportRead:
        """Store an uploaded PDF or Word résumé as a pending import;
        nothing reads it until import-resume is wired in"""
        if media_type not in self._limits.upload_types:
            raise InvalidInput("Upload a PDF or Word (.docx) file")
        if not content or len(content) > self._limits.max_upload_bytes:
            raise InvalidInput(
                f"The file must be between 1 byte and "
                f"{self._limits.max_upload_bytes // (1024 * 1024)} MB"
            )
        row = await self._repository.add(
            DocumentImport(
                user_id=user_id,
                filename=filename[:255],
                media_type=media_type,
                size=len(content),
                content=content,
            )
        )
        return ImportRead.model_validate(row, from_attributes=True)

    async def delete_import(self, user_id: UUID, import_id: UUID) -> None:
        """Remove an import and its file; a draft it made stays"""
        row = await self._repository.owned(DocumentImport, user_id, import_id)
        if row is None:
            raise NotFound("No such import")
        await self._repository.delete(row)

    async def _load(self, user_id: UUID, document_id: UUID) -> Document:
        """The user's document, or NotFound"""
        document = await self._repository.owned(Document, user_id, document_id)
        if document is None:
            raise NotFound("No such document")
        return document

    async def _read(self, document: Document) -> DocumentRead:
        """The document as the API returns it, flushed so updated_at is current"""
        await self._repository.flush()
        changesets = await self._repository.changesets([document.id])
        pending = _waiting(changesets)
        return DocumentRead(
            **_summary(document, _pending(changesets)).model_dump(),
            body=document.body,
            pending_body=_applied(document.body, pending.changeset.edits)
            if pending
            else None,
        )

    async def _keep(self, document: Document, label: str) -> DocumentVersion:
        """Copy the current draft into the next version"""
        return await self._repository.add(
            DocumentVersion(
                user_id=document.user_id,
                document_id=document.id,
                number=await self._repository.last_version_number(document.id) + 1,
                label=label,
                body=document.body,
            )
        )


__all__ = ["DocumentService"]
