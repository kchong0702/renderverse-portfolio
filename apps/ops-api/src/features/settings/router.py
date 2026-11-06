from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import User, current_user
from src.core.db.session import get_session
from src.features.settings.repository import SettingsRepository
from src.features.settings.schemas import SettingsRead, SettingsUpdate
from src.features.settings.service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


def get_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SettingsService:
    return SettingsService(SettingsRepository(session))


@router.get("")
async def read_settings(
    user: Annotated[User, Depends(current_user)],
    service: Annotated[SettingsService, Depends(get_service)],
) -> SettingsRead:
    return await service.get(user.id)


@router.patch("")
async def update_settings(
    patch: SettingsUpdate,
    user: Annotated[User, Depends(current_user)],
    service: Annotated[SettingsService, Depends(get_service)],
) -> SettingsRead:
    return await service.update(user.id, patch)
