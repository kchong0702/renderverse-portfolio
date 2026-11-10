from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.portfolio.schemas import DraftRead, ReleaseRead
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
