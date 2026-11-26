from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.agent_runner import ToolError
from src.core.exceptions import Conflict, InvalidInput, NotFound
from src.features.assistant.profile_edits import save_edits
from src.features.assistant.schemas import ProfileEdit, ProfileUpdated


class ProfileUpdateRequest(BaseModel):
    execute_tool: Literal["profile_update"]
    """A paused run asks to save changes the user approved"""

    edits: list[ProfileEdit]
    """The changes"""


async def profile_update(
    session: AsyncSession, user_id: UUID, request: ProfileUpdateRequest
) -> ProfileUpdated | ToolError:
    """Save the approved changes all or none; ToolError says why nothing came of it"""
    try:
        return await save_edits(session, user_id, request.edits)
    except (ValidationError, NotFound, InvalidInput, Conflict) as error:
        return ToolError(error=str(error))


__all__ = ["ProfileUpdateRequest", "profile_update"]
