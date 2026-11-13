from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.container import Container
from src.clients.ezcareer import ModelCatalog
from src.core.auth import CurrentUserDep
from src.core.config import get_settings
from src.db.session import SessionDep
from src.features.google import GoogleService
from src.features.settings.schemas import JSearchKey, SettingsRead, SettingsUpdate
from src.features.settings.service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


def settings_service(session: AsyncSession, container: Container) -> SettingsService:
    """The settings service on the session, its clients from the container"""
    settings = get_settings()
    return SettingsService(
        session,
        container.ezcareer(),
        GoogleService(session, container.google(), settings.google),
        settings.jsearch,
    )


def get_settings_service(session: SessionDep, request: Request) -> SettingsService:
    """The settings service on the request's database session"""
    return settings_service(session, request.app.state.container)


SettingsServiceDep = Annotated[SettingsService, Depends(get_settings_service)]


@router.get("")
async def read_settings(
    user: CurrentUserDep,
    service: SettingsServiceDep,
) -> SettingsRead:
    """The signed-in user's settings"""
    return await service.get(user.id)


@router.patch("")
async def update_settings(
    patch: SettingsUpdate,
    user: CurrentUserDep,
    service: SettingsServiceDep,
) -> SettingsRead:
    """Change some of the signed-in user's settings"""
    return await service.update(user.id, patch)


@router.get("/models")
async def read_models(
    _: CurrentUserDep,
    service: SettingsServiceDep,
) -> ModelCatalog:
    """The models the user can pick, from ezcareer-harness"""
    return await service.models()


@router.put("/connections/jsearch")
async def connect_jsearch(
    key: JSearchKey, user: CurrentUserDep, service: SettingsServiceDep
) -> SettingsRead:
    """Store the user's own JSearch API key, encrypted, for find runs to search with"""
    return await service.connect_jsearch(user.id, key.api_key)


@router.delete("/connections/jsearch")
async def disconnect_jsearch(
    user: CurrentUserDep, service: SettingsServiceDep
) -> SettingsRead:
    """Remove the user's JSearch API key, so find runs use the server's"""
    return await service.disconnect_jsearch(user.id)
