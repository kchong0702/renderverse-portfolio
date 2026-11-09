from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.core.auth import CurrentUserDep
from src.core.db.session import SessionDep
from src.features.profile.repository import ProfileRepository
from src.features.profile.schemas import (
    AgentProfile,
    EntryCreate,
    EntryRead,
    EntryWrite,
    ProfileRead,
    ProfileUpdate,
    SkillRead,
    SkillWrite,
)
from src.features.profile.service import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])


def get_profile_service(session: SessionDep) -> ProfileService:
    """The profile service on the request's database session"""
    return ProfileService(ProfileRepository(session))


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


@router.get("")
async def read_profile(user: CurrentUserDep, service: ProfileServiceDep) -> ProfileRead:
    """The signed-in user's details and job preferences"""
    return await service.get(user.id)


@router.patch("")
async def update_profile(
    patch: ProfileUpdate, user: CurrentUserDep, service: ProfileServiceDep
) -> ProfileRead:
    """Change some of the signed-in user's details or preferences"""
    return await service.update(user.id, patch)


@router.get("/agent")
async def read_agent_profile(
    user: CurrentUserDep, service: ProfileServiceDep
) -> AgentProfile:
    """The profile as ezcareer-harness's agents take it"""
    return await service.agent_profile(user.id)


@router.get("/entries")
async def list_entries(
    user: CurrentUserDep, service: ProfileServiceDep
) -> list[EntryRead]:
    """Every role, education and project, latest first"""
    return await service.entries(user.id)


@router.post("/entries", status_code=status.HTTP_201_CREATED)
async def add_entry(
    entry: EntryCreate, user: CurrentUserDep, service: ProfileServiceDep
) -> EntryRead:
    """Add a role, education or project"""
    return await service.add_entry(user.id, entry)


@router.put("/entries/{entry_id}")
async def replace_entry(
    entry_id: UUID, entry: EntryWrite, user: CurrentUserDep, service: ProfileServiceDep
) -> EntryRead:
    """Save every field of an entry but its kind"""
    return await service.replace_entry(user.id, entry_id, entry)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: UUID, user: CurrentUserDep, service: ProfileServiceDep
) -> None:
    """Delete an entry"""
    await service.delete_entry(user.id, entry_id)


@router.get("/skills")
async def list_skills(
    user: CurrentUserDep, service: ProfileServiceDep
) -> list[SkillRead]:
    """Every skill by group, then name"""
    return await service.skills(user.id)


@router.post("/skills", status_code=status.HTTP_201_CREATED)
async def add_skill(
    skill: SkillWrite, user: CurrentUserDep, service: ProfileServiceDep
) -> SkillRead:
    """Add a skill or spoken language"""
    return await service.add_skill(user.id, skill)


@router.put("/skills/{skill_id}")
async def replace_skill(
    skill_id: UUID, skill: SkillWrite, user: CurrentUserDep, service: ProfileServiceDep
) -> SkillRead:
    """Save every field of a skill"""
    return await service.replace_skill(user.id, skill_id, skill)


@router.delete("/skills/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: UUID, user: CurrentUserDep, service: ProfileServiceDep
) -> None:
    """Delete a skill"""
    await service.delete_skill(user.id, skill_id)
