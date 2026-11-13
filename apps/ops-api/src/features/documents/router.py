from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from document_schema import Changeset, DocumentKind, TemplateSpec
from fastapi import APIRouter, Depends, Header, Request, UploadFile, status
from fastapi.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.artifact import Render
from src.clients.ezcareer import Answer
from src.core.auth import CurrentUserDep
from src.core.config import get_settings
from src.db.session import SessionDep
from src.features.documents.schemas import (
    ChangesetDecision,
    ChangesetRead,
    DocumentCreate,
    DocumentEdits,
    DocumentMessage,
    DocumentRead,
    DocumentSummary,
    DocumentUpdate,
    VersionCreate,
    VersionRead,
)
from src.features.documents.service import DocumentService
from src.features.imports import ImportRead, ImportServiceDep, ImportSource
from src.features.profile import ProfileService
from src.features.settings import settings_service

if TYPE_CHECKING:
    from src.app.container import Container


router = APIRouter(prefix="/documents", tags=["documents"])


def document_service(session: AsyncSession, container: "Container") -> DocumentService:
    """The documents service on the session, its clients from the container"""
    return DocumentService(
        session,
        container.session_factory(),
        container.artifact(),
        get_settings().documents,
        ProfileService(session),
        settings_service(session, container),
        container.ezcareer(),
        container.runner(),
        container.tools(),
    )


def get_document_service(session: SessionDep, request: Request) -> DocumentService:
    """The documents service on the request's database session"""
    return document_service(session, request.app.state.container)


DocumentServiceDep = Annotated[DocumentService, Depends(get_document_service)]


@router.get("")
async def list_documents(
    user: CurrentUserDep, service: DocumentServiceDep
) -> list[DocumentSummary]:
    """Every résumé, CV and cover letter, masters first"""
    return await service.documents(user.id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_document(
    create: DocumentCreate, user: CurrentUserDep, service: DocumentServiceDep
) -> DocumentRead:
    """Add a document; its first draft is kept as version 1"""
    return await service.create(user.id, create)


@router.get("/templates")
async def list_templates(
    kind: DocumentKind, _: CurrentUserDep, service: DocumentServiceDep
) -> list[TemplateSpec]:
    """The templates a document of this kind can be printed with, from
    artifact-service"""
    return await service.templates(kind)


@router.get("/imports")
async def list_imports(
    user: CurrentUserDep, service: ImportServiceDep
) -> list[ImportRead]:
    """Every résumé uploaded in Documents, the latest first"""
    return await service.imports(user.id, ImportSource.DOCUMENTS)


@router.post("/imports", status_code=status.HTTP_201_CREATED)
async def start_import(
    file: UploadFile, user: CurrentUserDep, service: ImportServiceDep
) -> ImportRead:
    """Store a PDF or Word résumé and queue its import; an earlier import still
    queued or processing is abandoned"""
    return await service.upload(
        user.id,
        ImportSource.DOCUMENTS,
        file.filename or "resume",
        file.content_type or "",
        await file.read(),
    )


@router.delete("/imports/{import_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_import(
    import_id: UUID, user: CurrentUserDep, service: ImportServiceDep
) -> None:
    """Abandon an import still queued or processing"""
    await service.delete(user.id, import_id)


@router.get("/{document_id}")
async def read_document(
    document_id: UUID, user: CurrentUserDep, service: DocumentServiceDep
) -> DocumentRead:
    """One document with its current draft"""
    return await service.get(user.id, document_id)


@router.patch("/{document_id}")
async def update_document(
    document_id: UUID,
    patch: DocumentUpdate,
    user: CurrentUserDep,
    service: DocumentServiceDep,
) -> DocumentRead:
    """Rename a document"""
    return await service.update(user.id, document_id, patch)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID, user: CurrentUserDep, service: DocumentServiceDep
) -> None:
    """Delete a document with its versions and changesets"""
    await service.delete(user.id, document_id)


@router.post("/{document_id}/edits")
async def edit_document(
    document_id: UUID,
    edits: DocumentEdits,
    user: CurrentUserDep,
    service: DocumentServiceDep,
) -> DocumentRead:
    """Make the user's own edits to the draft, such as new wording or a new design"""
    return await service.edit(user.id, document_id, edits)


@router.put("/{document_id}/master")
async def set_master(
    document_id: UUID, user: CurrentUserDep, service: DocumentServiceDep
) -> DocumentRead:
    """Make the document the master of its kind"""
    return await service.set_master(user.id, document_id)


@router.get("/{document_id}/render")
async def render_document(
    document_id: UUID, user: CurrentUserDep, service: DocumentServiceDep
) -> Render:
    """The draft printed as a PDF by artifact-service, with its page report"""
    return await service.render(user.id, document_id)


@router.get("/{document_id}/versions")
async def list_versions(
    document_id: UUID, user: CurrentUserDep, service: DocumentServiceDep
) -> list[VersionRead]:
    """Every kept version, the latest first"""
    return await service.versions(user.id, document_id)


@router.post("/{document_id}/versions", status_code=status.HTTP_201_CREATED)
async def keep_version(
    document_id: UUID,
    create: VersionCreate,
    user: CurrentUserDep,
    service: DocumentServiceDep,
) -> VersionRead:
    """Keep the current draft as the next version"""
    return await service.keep_version(user.id, document_id, create)


@router.post("/{document_id}/versions/{version_id}/restore")
async def restore_version(
    document_id: UUID,
    version_id: UUID,
    user: CurrentUserDep,
    service: DocumentServiceDep,
) -> DocumentRead:
    """Put a kept version back as the draft"""
    return await service.restore(user.id, document_id, version_id)


@router.get("/{document_id}/changesets")
async def list_changesets(
    document_id: UUID, user: CurrentUserDep, service: DocumentServiceDep
) -> list[ChangesetRead]:
    """Every changeset proposed for the document, the latest first"""
    return await service.changesets(user.id, document_id)


@router.post("/{document_id}/changesets", status_code=status.HTTP_201_CREATED)
async def propose_changeset(
    document_id: UUID,
    changeset: Changeset,
    user: CurrentUserDep,
    service: DocumentServiceDep,
) -> ChangesetRead:
    """Store an agent's changeset for the user to answer; ezcareer-harness's
    edit-document workflow will send these once it is wired in"""
    return await service.propose(user.id, document_id, changeset)


@router.delete("/{document_id}/changesets/{changeset_id}/edits/{index}")
async def undo_edit(
    document_id: UUID,
    changeset_id: UUID,
    index: int,
    user: CurrentUserDep,
    service: DocumentServiceDep,
) -> ChangesetRead:
    """Take one edit out of the pending changeset; the last one closes it"""
    return await service.undo_edit(user.id, document_id, changeset_id, index)


@router.put("/{document_id}/changesets/{changeset_id}")
async def decide_changeset(
    document_id: UUID,
    changeset_id: UUID,
    decision: ChangesetDecision,
    user: CurrentUserDep,
    service: DocumentServiceDep,
) -> ChangesetRead:
    """Accept every edit of the changeset into the draft, or reject it"""
    return await service.decide(user.id, document_id, changeset_id, decision)


@router.post("/{document_id}/chat/messages")
async def chat(
    document_id: UUID,
    message: DocumentMessage,
    user: CurrentUserDep,
    service: DocumentServiceDep,
) -> EventSourceResponse:
    """Ask edit-document about the document and stream the turn, with any changeset it
    stored for review, until it replies, asks back, fails or is stopped"""
    return EventSourceResponse(await service.chat(user.id, document_id, message.text))


@router.post("/{document_id}/chat/tasks/{task_id}/answer")
async def answer_chat(
    document_id: UUID,
    task_id: str,
    answer: Answer,
    user: CurrentUserDep,
    service: DocumentServiceDep,
) -> EventSourceResponse:
    """Answer the widget a paused chat turn asked, and stream the rest of it"""
    return EventSourceResponse(
        await service.answer_chat(user.id, document_id, task_id, answer)
    )


@router.get("/{document_id}/chat/stream")
async def resume_chat(
    document_id: UUID,
    user: CurrentUserDep,
    service: DocumentServiceDep,
    last_event_id: Annotated[str | None, Header()] = None,
) -> EventSourceResponse:
    """Resume the chat's turn after the Last-Event-ID the client last saw"""
    return EventSourceResponse(
        await service.resume_chat(user.id, document_id, last_event_id)
    )


@router.post(
    "/{document_id}/chat/tasks/{task_id}/cancel",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def cancel_chat(
    document_id: UUID, task_id: str, user: CurrentUserDep, service: DocumentServiceDep
) -> None:
    """Stop the chat's running turn; the user's Stop button"""
    await service.cancel_chat(user.id, document_id, task_id)
