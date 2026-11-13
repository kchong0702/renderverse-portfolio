from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.core.auth import CurrentUserDep
from src.core.config import get_settings
from src.db.session import SessionDep
from src.features.imports.schemas import ImportRead
from src.features.imports.service import ImportService

router = APIRouter(prefix="/imports", tags=["imports"])


def get_import_service(session: SessionDep, request: Request) -> ImportService:
    """The imports service on the request's database session and the app's storage"""
    return ImportService(
        session,
        request.app.state.storage,
        get_settings().documents,
        get_settings().profile,
    )


ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]


@router.get("/active")
async def list_active_imports(
    user: CurrentUserDep, service: ImportServiceDep
) -> list[ImportRead]:
    """The user's imports still queued or processing, from Documents and Data"""
    return await service.active(user.id)
