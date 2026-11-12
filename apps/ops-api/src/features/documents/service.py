from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import suppress
from datetime import timedelta
from functools import partial
from pathlib import PurePath
from uuid import UUID, uuid4

from document_schema import (
    AnyDocument,
    AnyEdit,
    Changeset,
    ChangesetStatus,
    DocumentKind,
    TemplateSpec,
    apply_edits,
)
from pydantic import BaseModel, TypeAdapter, ValidationError
from rapidfuzz import fuzz, process, utils
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.artifact import ArtifactClient, Render
from src.clients.ezcareer import (
    Answer,
    Completed,
    DataRequest,
    EzcareerClient,
    Failed,
    InputRequired,
    Published,
    RunEvent,
)
from src.core.config import DocumentsSettings
from src.core.exceptions import (
    Conflict,
    InvalidInput,
    NotFound,
    ServiceUnavailable,
)
from src.core.logging import get_logger
from src.core.runner import Runner
from src.db.base import utcnow
from src.db.session import session_scope
from src.features.documents.enums import ImportStatus
from src.features.documents.models import (
    Document,
    DocumentChangeset,
    DocumentImport,
    DocumentVersion,
)
from src.features.documents.repository import DocumentRepository
from src.features.documents.schemas import (
    ChangesetDecision,
    ChangesetProposed,
    ChangesetRead,
    DocumentAnswer,
    DocumentCreate,
    DocumentEdits,
    DocumentMatch,
    DocumentRead,
    DocumentRequest,
    DocumentsAnswer,
    DocumentsRequest,
    DocumentSummary,
    DocumentUpdate,
    EditDocumentInput,
    EditDocumentOutput,
    FetchError,
    ImportRead,
    ImportResumeInput,
    ImportResumeOutput,
    LineRead,
    TailoredDocument,
    VersionCreate,
    VersionRead,
)
from src.features.profile import ImportSource, ProfileService, resume_profile
from src.features.settings import SettingsService

logger = get_logger(__name__)


def _pending(changesets: Sequence[DocumentChangeset]) -> int:
    """How many of these changesets wait for the user's answer"""
    return sum(row.status is ChangesetStatus.PENDING for row in changesets)


def _waiting(changesets: Sequence[DocumentChangeset]) -> DocumentChangeset | None:
    """The changeset still waiting for the user's answer, if any"""
    return next(
        (row for row in changesets if row.status is ChangesetStatus.PENDING),
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


async def _load(
    repository: DocumentRepository, user_id: UUID, document_id: UUID
) -> Document:
    """The user's document, or NotFound"""
    document = await repository.owned(Document, user_id, document_id)
    if document is None:
        raise NotFound("No such document")
    return document


async def _propose(
    repository: DocumentRepository, document: Document, changeset: Changeset
) -> DocumentChangeset:
    """Store an agent's changeset for the user to accept or reject, adding its edits to
    the one still pending; it must be pending and its edits fit the current draft"""
    if changeset.status is not ChangesetStatus.PENDING:
        raise InvalidInput("A new changeset must be pending")
    pending = _waiting(await repository.changesets([document.id]))
    edits = [*(pending.edits if pending else []), *changeset.edits]
    try:
        apply_edits(document.body, edits)
    except ValueError as error:
        raise InvalidInput(str(error)) from error
    if pending:
        pending.edits = edits
        pending.reason = changeset.reason
        await repository.flush()
        return pending
    return await repository.add(
        DocumentChangeset(
            user_id=document.user_id,
            document_id=document.id,
            key=changeset.id,
            agent=changeset.agent,
            reason=changeset.reason,
            edits=changeset.edits,
        )
    )


class DocumentService:
    def __init__(
        self,
        session: AsyncSession,
        factory: async_sessionmaker[AsyncSession],
        artifact: ArtifactClient,
        limits: DocumentsSettings,
        profile: ProfileService,
        settings: SettingsService,
        ezcareer: EzcareerClient,
        runner: Runner,
    ):
        """Hold the session, its repository and a factory for sessions runs outlive,
        artifact-service, the documents limit, and what the agents use and run on"""
        self._session = session
        self._repository = DocumentRepository(session)
        self._factory = factory
        self._artifact = artifact
        self._limits = limits
        self._profile = profile
        self._settings = settings
        self._ezcareer = ezcareer
        self._runner = runner

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
        return await self._read(await _load(self._repository, user_id, document_id))

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
        document = await _load(self._repository, user_id, document_id)
        if patch.title is not None:
            document.title = patch.title
        return await self._read(document)

    async def edit(
        self, user_id: UUID, document_id: UUID, edits: DocumentEdits
    ) -> DocumentRead:
        """Make the user's own edits to the current draft"""
        document = await _load(self._repository, user_id, document_id)
        try:
            document.body = apply_edits(document.body, edits.edits)
        except ValueError as error:
            raise InvalidInput(str(error)) from error
        return await self._read(document)

    async def set_master(self, user_id: UUID, document_id: UUID) -> DocumentRead:
        """Make a document the master of its kind, in place of any other"""
        document = await _load(self._repository, user_id, document_id)
        await self._repository.clear_master(user_id, document.kind)
        document.master = True
        return await self._read(document)

    async def delete(self, user_id: UUID, document_id: UUID) -> None:
        """Remove a document with its versions and changesets; Conflict for a master"""
        document = await _load(self._repository, user_id, document_id)
        if document.master:
            raise Conflict(
                f"Set another {document.kind.value.replace('_', ' ')} as master"
                " before deleting this one"
            )
        await self._repository.delete(document)

    async def templates(self, kind: DocumentKind) -> list[TemplateSpec]:
        """The templates a document of this kind can be printed with"""
        return await self._artifact.templates(kind)

    async def render(self, user_id: UUID, document_id: UUID) -> Render:
        """The current draft printed as a PDF, with how its pages came out"""
        return await self._artifact.render(
            (await _load(self._repository, user_id, document_id)).body
        )

    async def versions(self, user_id: UUID, document_id: UUID) -> list[VersionRead]:
        """Every kept version of a document, the latest first"""
        document = await _load(self._repository, user_id, document_id)
        return [
            VersionRead.model_validate(version, from_attributes=True)
            for version in await self._repository.versions(document.id)
        ]

    async def keep_version(
        self, user_id: UUID, document_id: UUID, create: VersionCreate
    ) -> VersionRead:
        """Keep the current draft as the next version"""
        document = await _load(self._repository, user_id, document_id)
        version = await self._keep(document, create.label)
        return VersionRead.model_validate(version, from_attributes=True)

    async def restore(
        self, user_id: UUID, document_id: UUID, version_id: UUID
    ) -> DocumentRead:
        """Keep the current draft as a version, then put a kept version back as the
        draft"""
        document = await _load(self._repository, user_id, document_id)
        version = await self._repository.version(document.id, version_id)
        if version is None:
            raise NotFound("No such version")
        await self._keep(document, f"Before restoring version {version.number}")
        document.body = version.body
        return await self._read(document)

    async def changesets(self, user_id: UUID, document_id: UUID) -> list[ChangesetRead]:
        """Every changeset proposed for a document, the latest first"""
        document = await _load(self._repository, user_id, document_id)
        return [
            ChangesetRead.model_validate(row, from_attributes=True)
            for row in await self._repository.changesets([document.id])
        ]

    async def propose(
        self, user_id: UUID, document_id: UUID, changeset: Changeset
    ) -> ChangesetRead:
        """Store an agent's changeset for the user to accept or reject, adding its edits
        to the one still pending; the edits must apply to the current draft"""
        row = await _propose(
            self._repository,
            await _load(self._repository, user_id, document_id),
            changeset,
        )
        return ChangesetRead.model_validate(row, from_attributes=True)

    async def undo_edit(
        self, user_id: UUID, document_id: UUID, changeset_id: UUID, index: int
    ) -> ChangesetRead:
        """Take one edit out of a pending changeset, closing it as rejected when none
        is left; Conflict when the edits left no longer fit the draft"""
        document = await _load(self._repository, user_id, document_id)
        row = await self._repository.changeset(document.id, changeset_id)
        if row is None or not 0 <= index < len(row.edits):
            raise NotFound("No such edit")
        if row.status is not ChangesetStatus.PENDING:
            raise Conflict("This changeset is already answered")
        edits = [e for i, e in enumerate(row.edits) if i != index]
        if not edits:
            row.status = ChangesetStatus.REJECTED
            row.decided_at = utcnow()
        else:
            try:
                apply_edits(document.body, edits)
            except ValueError as error:
                raise Conflict(
                    f"The other edits need this one to fit the document: {error}"
                ) from error
            row.edits = edits
        return ChangesetRead.model_validate(row, from_attributes=True)

    async def propose_from_run(
        self, user_id: UUID, document_id: UUID, changeset: Changeset
    ) -> ChangesetProposed | None:
        """Store a changeset a run proposed on a session of its own, since the run
        outlives the request's; None, logged, when it doesn't fit or has no document"""
        try:
            async for session in session_scope(self._factory):
                repository = DocumentRepository(session)
                document = await _load(repository, user_id, document_id)
                row = await _propose(repository, document, changeset)
                proposed = ChangesetProposed(
                    document_id=document.id,
                    title=document.title,
                    changeset_id=row.id,
                    edits=len(row.edits),
                )
        except (NotFound, InvalidInput) as error:
            logger.warning("changeset_skipped", reason=error.message)
            return None
        return proposed

    async def answer_data_request(
        self, user_id: UUID, request: DataRequest
    ) -> DocumentsAnswer | DocumentAnswer | FetchError:
        """Answer a paused run's request for the user's documents, the best match for
        a name first, or for one document, on a session of its own"""
        try:
            parsed = TypeAdapter(DocumentsRequest | DocumentRequest).validate_python(
                request.model_dump()
            )
        except ValidationError as error:
            return FetchError(error=str(error))
        async for session in session_scope(self._factory):
            repository = DocumentRepository(session)
            match parsed:
                case DocumentRequest(id=document_id):
                    document = await repository.owned(Document, user_id, document_id)
                    answer = (
                        DocumentAnswer(document=document.body, lines=document.lines)
                        if document
                        else FetchError(error="No such document")
                    )
                case DocumentsRequest(name=name, kind=kind):
                    documents = [
                        d
                        for d in await repository.documents(user_id)
                        if kind is None or d.kind is kind
                    ]
                    if name:
                        documents = [
                            documents[index]
                            for _, _, index in process.extract(
                                name,
                                [
                                    f"{d.title} {d.kind.value.replace('_', ' ')}"
                                    for d in documents
                                ],
                                scorer=fuzz.partial_token_sort_ratio,
                                processor=utils.default_process,
                                score_cutoff=self._limits.match_cutoff,
                                limit=None,
                            )
                        ]
                    answer = DocumentsAnswer(
                        documents=[
                            DocumentMatch.model_validate(d, from_attributes=True)
                            for d in documents
                        ]
                    )
        return answer

    async def decide(
        self,
        user_id: UUID,
        document_id: UUID,
        changeset_id: UUID,
        decision: ChangesetDecision,
    ) -> ChangesetRead:
        """Accept a changeset, applying every edit to the draft and keeping a version,
        or reject it; Conflict once it is answered or when its edits no longer fit"""
        document = await _load(self._repository, user_id, document_id)
        row = await self._repository.changeset(document.id, changeset_id)
        if row is None:
            raise NotFound("No such changeset")
        if row.status is decision.status:
            return ChangesetRead.model_validate(row, from_attributes=True)
        if row.status is not ChangesetStatus.PENDING:
            raise Conflict("This changeset is already answered")
        if decision.status is ChangesetStatus.ACCEPTED:
            try:
                edited = apply_edits(document.body, row.edits)
            except ValueError as error:
                raise Conflict(
                    f"These edits no longer fit the document: {error}"
                ) from error
            await self._keep(document, f"Before {row.agent}'s edits")
            document.body = edited
        row.status = decision.status
        row.decided_at = utcnow()
        return ChangesetRead.model_validate(row, from_attributes=True)

    async def copy_for_job(
        self, user_id: UUID, job_id: UUID, kind: DocumentKind, title: str
    ) -> Document | None:
        """The job's copy of the master of this kind, made the first time; None
        without a master, Conflict when the user keeps the most of this kind"""
        documents = await self._repository.documents(user_id)
        document = next(
            (d for d in documents if d.job_id == job_id and d.kind is kind), None
        )
        if document is not None:
            return document
        master = next((d for d in documents if d.master and d.kind is kind), None)
        if master is None:
            return None
        await self._make_room(user_id, kind)
        try:
            document = await self._repository.add(
                Document(
                    user_id=user_id,
                    kind=kind,
                    title=title,
                    body=master.body,
                    lines=master.lines,
                    job_id=job_id,
                )
            )
        except IntegrityError as error:
            raise Conflict("This job's documents are already being tailored") from error
        await self._keep(document, f"Copied from {master.title}")
        return document

    async def tailor(
        self, user_id: UUID, document: Document, text: str
    ) -> TailoredDocument:
        """Start the copy's chat turn on text unless a changeset still waits for the
        user; a turn already running carries on"""
        waiting = any(
            row.status is ChangesetStatus.PENDING
            for row in await self._repository.changesets([document.id])
        )
        if not waiting:
            with suppress(Conflict):
                await self.chat(user_id, document.id, text)
        return TailoredDocument(document_id=document.id, tailoring=not waiting)

    async def _chat_events(
        self,
        user_id: UUID,
        document_id: UUID,
        events: AsyncIterator[RunEvent[EditDocumentOutput]],
    ) -> AsyncIterator[BaseModel]:
        """A chat turn's events as the browser gets them: a changeset the run
        proposes is stored and announced before its reply, which ends the turn"""
        async for event in events:
            if isinstance(event, Completed):
                if event.reply.changeset and (
                    proposed := await self.propose_from_run(
                        user_id, document_id, event.reply.changeset
                    )
                ):
                    yield proposed
                yield Completed(reply=event.reply.reply)
            elif not isinstance(event, Published):
                yield event

    async def chat(
        self, user_id: UUID, document_id: UUID, text: str
    ) -> AsyncIterator[str]:
        """Start a turn of the document's chat and return its events as they come;
        Conflict while a turn runs"""
        context_id = f"{user_id}:document:{document_id}"
        await _load(self._repository, user_id, document_id)
        data = EditDocumentInput(
            document_id=document_id,
            facts=(await self._profile.agent_profile(user_id)).facts,
        )
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        return await self._runner.start_task(
            user_id,
            context_id,
            "edit-document",
            self._chat_events(
                user_id,
                document_id,
                self._ezcareer.stream(
                    "edit-document",
                    EditDocumentOutput,
                    user_id=user_id,
                    context_id=context_id,
                    text=text,
                    data=data,
                    metadata=metadata,
                    answer_data_request=partial(self.answer_data_request, user_id),
                ),
            ),
        )

    async def answer_chat(
        self, user_id: UUID, document_id: UUID, task_id: str, answer: Answer
    ) -> AsyncIterator[str]:
        """Answer the widget a paused turn of the document's chat asked and return the
        rest of the turn's events as they come; Conflict while a turn runs"""
        context_id = f"{user_id}:document:{document_id}"
        await _load(self._repository, user_id, document_id)
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        return await self._runner.start_task(
            user_id,
            context_id,
            "edit-document",
            self._chat_events(
                user_id,
                document_id,
                self._ezcareer.stream_resume(
                    "edit-document",
                    EditDocumentOutput,
                    user_id=user_id,
                    context_id=context_id,
                    task_id=task_id,
                    answer=answer,
                    metadata=metadata,
                    answer_data_request=partial(self.answer_data_request, user_id),
                ),
            ),
        )

    async def resume_chat(
        self, user_id: UUID, document_id: UUID, last_event_id: str | None
    ) -> AsyncIterator[str]:
        """The document chat's current turn after the Last-Event-ID the client last
        saw; NotFound when there is none to resume"""
        return await self._runner.resume(
            f"{user_id}:document:{document_id}", last_event_id
        )

    async def cancel_chat(self, user_id: UUID, document_id: UUID, task_id: str) -> None:
        """Stop the running turn of the document's chat"""
        await self._ezcareer.cancel(
            "edit-document", task_id, f"{user_id}:document:{document_id}"
        )

    async def imports(self, user_id: UUID) -> list[ImportRead]:
        """Every uploaded résumé file, the latest first"""
        return [
            ImportRead.model_validate(row, from_attributes=True)
            for row in await self._repository.imports(user_id)
        ]

    async def start_import(
        self, user_id: UUID, filename: str, media_type: str, content: bytes
    ) -> ImportRead:
        """Store an uploaded PDF or Word résumé as a pending import for
        read_import to run import-resume on"""
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

    async def read_import(self, user_id: UUID, import_id: UUID) -> ImportRead:
        """Claim a pending or failed import and run import-resume on it with no
        transaction open: it becomes a draft and syncs the profile, or fails"""
        row = await self._repository.claim_import(
            user_id,
            import_id,
            utcnow() - timedelta(seconds=self._ezcareer.run_timeout_seconds),
        )
        if row is None:
            if await self._repository.owned(DocumentImport, user_id, import_id) is None:
                raise NotFound("No such import")
            raise Conflict("This import is already done or being read")
        data = ImportResumeInput(file=await self._repository.file(row))
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        try:
            run = await self._ezcareer.send(
                "import-resume",
                ImportResumeOutput,
                user_id=user_id,
                context_id=f"{user_id}:{uuid4()}",
                data=data,
                metadata=metadata,
            )
        except ServiceUnavailable:
            row.status = ImportStatus.PENDING
            await self._session.commit()
            raise
        match run:
            case Completed(reply=reply):
                await self._profile.sync(
                    user_id,
                    ImportSource.DOCUMENTS,
                    row.filename,
                    row.media_type,
                    data.file,
                    resume_profile(reply.document.content),
                )
                try:
                    await self._make_room(user_id, reply.document.kind)
                except Conflict as error:
                    row.status = ImportStatus.FAILED
                    row.error = error.message
                else:
                    document = await self._repository.add(
                        Document(
                            user_id=user_id,
                            kind=reply.document.kind,
                            title=PurePath(row.filename).stem[:200] or "Résumé",
                            body=reply.document,
                            lines=reply.lines,
                        )
                    )
                    await self._keep(document, "Imported")
                    row.status = ImportStatus.DONE
                    row.document_id = document.id
                    row.suggestion = reply.suggestion
                    row.error = ""
            case InputRequired():
                row.status = ImportStatus.FAILED
                row.error = "import-resume asked for input ops cannot give"
            case Failed(reason=reason):
                row.status = ImportStatus.FAILED
                row.error = reason
        await self._repository.flush()
        return ImportRead.model_validate(row, from_attributes=True)

    async def delete_import(self, user_id: UUID, import_id: UUID) -> None:
        """Remove an import and its file; a draft it made stays"""
        row = await self._repository.owned(DocumentImport, user_id, import_id)
        if row is None:
            raise NotFound("No such import")
        await self._repository.delete(row)

    async def _read(self, document: Document) -> DocumentRead:
        """The document as the API returns it, flushed so updated_at is current"""
        await self._repository.flush()
        changesets = await self._repository.changesets([document.id])
        pending = _waiting(changesets)
        return DocumentRead(
            **_summary(document, _pending(changesets)).model_dump(),
            body=document.body,
            lines=[LineRead(id=line.id, text=line.text) for line in document.lines],
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
