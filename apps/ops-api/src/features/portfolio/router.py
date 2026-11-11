from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Path, Request, status
from fastapi.responses import FileResponse

from src.clients.storage import UploadTarget
from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.portfolio.enums import MediaSlot, MediaType
from src.features.portfolio.schemas import (
    AssetRead,
    DraftRead,
    MediaChoice,
    ReleaseRead,
    Upload,
)
from src.features.portfolio.service import PortfolioService

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


def get_portfolio_service(session: SessionDep, request: Request) -> PortfolioService:
    """The portfolio service on the request's database session and the app's
    storage"""
    return PortfolioService(session, request.app.state.storage)


@router.get("/draft")
async def read_draft(
    user: CurrentUserDep,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> DraftRead:
    """What publishing now would change on the site"""
    return await service.draft(user.id)


@router.get("/releases")
async def list_releases(
    user: CurrentUserDep,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> list[ReleaseRead]:
    """Every release, latest first"""
    return await service.releases(user.id)


@router.post("/releases", status_code=status.HTTP_201_CREATED)
async def publish(
    user: CurrentUserDep,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> ReleaseRead:
    """Publish the draft as the next release; 409 when nothing has changed"""
    return await service.publish(user.id)


@router.post("/releases/{release_id}/live")
async def make_live(
    release_id: UUID,
    user: CurrentUserDep,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> ReleaseRead:
    """Serve this release instead of the live one, to roll back or forward"""
    return await service.make_live(user.id, release_id)


@router.post("/uploads")
async def request_upload(
    upload: Upload,
    user: CurrentUserDep,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> UploadTarget:
    """Where to PUT a file; 422 for a type or size the site does not take"""
    return service.upload_target(user.id, upload)


@router.put("/uploads/{sha256}", status_code=status.HTTP_204_NO_CONTENT)
async def receive_upload(
    sha256: Annotated[str, Path(pattern=r"^[0-9a-f]{64}$")],
    content_type: Annotated[MediaType, Header()],
    request: Request,
    user: CurrentUserDep,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> None:
    """The local storage's upload target; 404 once R2 is set up"""
    await service.receive_upload(user.id, sha256, content_type, request.stream())


@router.get("/uploads/{sha256}")
async def read_upload(
    sha256: str,
    user: CurrentUserDep,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> FileResponse:
    """The local storage's preview URL; 404 once R2 is set up"""
    path, media_type = await service.uploaded_file(user.id, sha256)
    return FileResponse(path, media_type=media_type)


@router.post("/assets", status_code=status.HTTP_201_CREATED)
async def add_asset(
    upload: Upload,
    user: CurrentUserDep,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> AssetRead:
    """Keep a file once it is uploaded; 409 when storage does not hold it yet"""
    return await service.add_asset(user.id, upload)


@router.get("/assets")
async def list_assets(
    user: CurrentUserDep,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> list[AssetRead]:
    """Every uploaded file, latest first, with the projects showing it"""
    return await service.assets(user.id)


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID,
    user: CurrentUserDep,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> None:
    """Delete a file; 409 while a project shows it"""
    await service.delete_asset(user.id, asset_id)


@router.put("/projects/{project_id}/{slot}", status_code=status.HTTP_204_NO_CONTENT)
async def choose_media(
    project_id: UUID,
    slot: MediaSlot,
    choice: MediaChoice,
    user: CurrentUserDep,
    service: Annotated[PortfolioService, Depends(get_portfolio_service)],
) -> None:
    """Show a file as the project's image or video, or show none"""
    await service.choose_media(user.id, project_id, slot, choice.asset_id)
