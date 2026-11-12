from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, UploadFile, status

from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.imports import (
    ImportRead,
    ImportServiceDep,
    ImportSource,
    ImportStatus,
)
from src.features.profile.runs import ProfileRunService
from src.features.profile.schemas import (
    AgentProfile,
    ChangeAnswers,
    ChangeRead,
    EntryCreate,
    EntryRead,
    EntryWrite,
    NetworkingRead,
    NetworkingWrite,
    ProfileRead,
    ProfileUpdate,
    SkillRead,
    SkillWrite,
)
from src.features.profile.service import ProfileService
from src.features.settings import SettingsServiceDep

router = APIRouter(prefix="/profile", tags=["profile"])


def get_profile_service(session: SessionDep) -> ProfileService:
    """The profile service on the request's database session"""
    return ProfileService(session)


ProfileServiceDep = Annotated[ProfileService, Depends(get_profile_service)]


def get_profile_run_service(
    session: SessionDep,
    profile: ProfileServiceDep,
    settings: SettingsServiceDep,
    request: Request,
) -> ProfileRunService:
    """The service that runs the harness on the profile, on the request's session"""
    return ProfileRunService(session, profile, settings, request.app.state.ezcareer)


ProfileRunServiceDep = Annotated[ProfileRunService, Depends(get_profile_run_service)]


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


@router.get("/imports")
async def list_imports(
    user: CurrentUserDep, service: ImportServiceDep
) -> list[ImportRead]:
    """Every import into the profile, from Data and Documents, with what it added,
    conflicted and matched"""
    return await service.imports(user.id)


@router.post("/imports", status_code=status.HTTP_201_CREATED)
async def import_file(
    file: UploadFile,
    user: CurrentUserDep,
    service: ImportServiceDep,
    response: Response,
) -> ImportRead:
    """Store a résumé (PDF or Word) or a profile export (.zip) and queue its
    import; a file imported before is returned as it was, with a 200"""
    imported = await service.upload(
        user.id,
        ImportSource.DATA,
        file.filename or "import",
        file.content_type or "",
        await file.read(),
    )
    if imported.status is ImportStatus.DONE:
        response.status_code = status.HTTP_200_OK
    return imported


@router.get("/changes")
async def list_changes(
    user: CurrentUserDep, service: ProfileServiceDep
) -> list[ChangeRead]:
    """Every change imports left for the user to settle"""
    return await service.changes(user.id)


@router.post("/changes/resolve")
async def resolve_changes(
    answers: ChangeAnswers, user: CurrentUserDep, service: ProfileServiceDep
) -> list[ChangeRead]:
    """Settle some pending changes and return the ones still pending"""
    return await service.resolve(user.id, answers)


@router.get("/networking")
async def read_networking(
    user: CurrentUserDep, service: ProfileServiceDep
) -> NetworkingRead:
    """The latest copy to paste into job portals"""
    return await service.networking(user.id)


@router.post("/networking")
async def write_networking(
    request: NetworkingWrite, user: CurrentUserDep, service: ProfileRunServiceDep
) -> NetworkingRead:
    """Write the copy again, or only its headline, summary or one description"""
    return await service.write_networking(user.id, request)
