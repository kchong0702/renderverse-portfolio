from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.auth import CurrentUserDep
from src.core.db.session import SessionDep
from src.features.settings.repository import SettingsRepository
from src.features.settings.schemas import SettingsRead, SettingsUpdate
from src.features.settings.service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


def get_settings_service(session: SessionDep) -> SettingsService:
    """The settings service on the request's database session"""
    return SettingsService(SettingsRepository(session))


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
