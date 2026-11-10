from typing import NotRequired

from src.agents.state import ProfileState
from src.shared.jobs import JobSearch
from src.shared.profile import Preferences


class JobFinderState(ProfileState):
    preferences: Preferences
    """What the user wants from a job"""

    search: NotRequired[JobSearch | None]
    """The user's own search, whose fields search_jobs uses over the agent's"""
