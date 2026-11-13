from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ValidationError

from src.core.agent_runner import ToolError
from src.core.exceptions import InvalidInput, NotFound
from src.features.assistant.profile_edits import ProfileEdits
from src.features.assistant.schemas import ProfileSyncPreview


class ProfileSyncRequest(BaseModel):
    execute_tool: Literal["profile_sync"]
    """A paused run asks what syncing a document into the profile would change"""

    document_id: UUID
    """The résumé or CV"""


async def profile_sync(
    edits: ProfileEdits, user_id: UUID, request: ProfileSyncRequest
) -> ProfileSyncPreview | ToolError:
    """What syncing a résumé or CV into the profile would change; ToolError says why
    nothing came of it"""
    try:
        return await edits.preview(user_id, request.document_id)
    except (ValidationError, NotFound, InvalidInput) as error:
        return ToolError(error=str(error))


__all__ = ["ProfileSyncRequest", "profile_sync"]
