from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.runner import Tool, Tools
from src.features.assistant.profile_edits import ProfileEdits
from src.features.assistant.tools.profile_sync import ProfileSyncRequest, profile_sync
from src.features.assistant.tools.profile_update import (
    ProfileUpdateRequest,
    profile_update,
)


def profile_tools(factory: async_sessionmaker[AsyncSession]) -> Tools:
    """The profile edits' tools"""
    edits = ProfileEdits(factory)
    return {
        "profile_sync": Tool(ProfileSyncRequest, partial(profile_sync, edits)),
        "profile_update": Tool(ProfileUpdateRequest, partial(profile_update, edits)),
    }


__all__ = ["profile_tools"]
