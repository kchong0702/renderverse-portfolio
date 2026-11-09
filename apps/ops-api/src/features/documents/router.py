from typing import Annotated
from uuid import UUID

from document_schema import Changeset, DocumentKind, TemplateSpec
from fastapi import APIRouter, Depends, Request, UploadFile, status

from src.clients.artifact import Render
from src.clients.ezcareer import Answer, Run
from src.core.auth import CurrentUserDep
from src.core.config import get_settings
from src.db.session import SessionDep
from src.features.documents.schemas import (
    ChangesetDecision,
    ChangesetRead,
    DocumentCreate,
    DocumentEdits,
    DocumentRead,
    DocumentSummary,
    DocumentUpdate,
    EditRequest,
    ImportRead,
    VersionCreate,
    VersionRead,
)
from src.features.documents.service import DocumentService
from src.features.profile import ProfileServiceDep
from src.features.settings import SettingsServiceDep

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(
    session: SessionDep,
    profile: ProfileServiceDep,
    settings: SettingsServiceDep,
    request: Request,
) -> DocumentService:
    """The documents service on the request's database session, and the profile
    and settings services"""
    return DocumentService(
        session,
        request.app.state.artifact,
        get_settings().documents,
        profile,
        settings,
        request.app.state.ezcareer,
    )


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
    user: CurrentUserDep, service: DocumentServiceDep
) -> list[ImportRead]:
    """Every uploaded résumé file, the latest first"""
    return await service.imports(user.id)


@router.post("/imports", status_code=status.HTTP_201_CREATED)
async def start_import(
    file: UploadFile, user: CurrentUserDep, service: DocumentServiceDep
) -> ImportRead:
    """Store a PDF or Word résumé as a pending import; POST its read to turn it
    into a draft"""
    return await service.start_import(
        user.id, file.filename or "resume", file.content_type or "", await file.read()
    )


@router.post("/imports/{import_id}/read")
async def read_import(
    import_id: UUID, user: CurrentUserDep, service: DocumentServiceDep
) -> ImportRead:
    """Run import-resume on the file: the import comes back done with its draft,
    or failed with the reason"""
    return await service.read_import(user.id, import_id)


@router.delete("/imports/{import_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_import(
    import_id: UUID, user: CurrentUserDep, service: DocumentServiceDep
) -> None:
    """Remove an import and its file"""
    await service.delete_import(user.id, import_id)


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


@router.post("/{document_id}/edit-requests/{request_id}")
async def request_edit(
    document_id: UUID,
    request_id: UUID,
    request: EditRequest,
    user: CurrentUserDep,
    service: DocumentServiceDep,
) -> Run[ChangesetRead]:
    """Ask edit-document for a change: its changeset is stored for review, or it
    asks back with a widget, or fails"""
    return await service.request_edit(user.id, document_id, request_id, request)


@router.post("/{document_id}/edit-requests/{request_id}/tasks/{task_id}/answer")
async def answer_edit(
    document_id: UUID,
    request_id: UUID,
    task_id: str,
    answer: Answer,
    user: CurrentUserDep,
    service: DocumentServiceDep,
) -> Run[ChangesetRead]:
    """Answer the widget a paused edit request asked; the run goes on"""
    return await service.answer_edit(user.id, document_id, request_id, task_id, answer)
