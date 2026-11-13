from typing import Annotated

from fastapi import APIRouter, Depends

from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.preferences.schemas import PreferencesRead, PreferencesUpdate
from src.features.preferences.service import PreferencesService

router = APIRouter(prefix="/preferences", tags=["preferences"])


def get_preferences_service(session: SessionDep) -> PreferencesService:
    """The preferences service on the request's database session"""
    return PreferencesService(session)


PreferencesServiceDep = Annotated[PreferencesService, Depends(get_preferences_service)]


@router.get("")
async def read_preferences(
    user: CurrentUserDep, service: PreferencesServiceDep
) -> PreferencesRead:
    """The signed-in user's job preferences"""
    return await service.get(user.id)


@router.patch("")
async def update_preferences(
    patch: PreferencesUpdate, user: CurrentUserDep, service: PreferencesServiceDep
) -> PreferencesRead:
    """Change some of the signed-in user's job preferences"""
    return await service.update(user.id, patch)
