from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.settings.schemas import SettingsRead, SettingsUpdate
from src.features.settings.service import SettingsService
from src.integrations.ezcareer import ModelCatalog

router = APIRouter(prefix="/settings", tags=["settings"])


def get_settings_service(session: SessionDep, request: Request) -> SettingsService:
    """The settings service on the request's database session"""
    return SettingsService(session, request.app.state.ezcareer)


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
