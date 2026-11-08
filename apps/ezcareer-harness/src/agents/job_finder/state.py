from src.agents.state import ProfileState
from src.shared.models import Preferences


class JobFinderState(ProfileState):
    preferences: Preferences
    """What the user wants from a job, which search_jobs filters by"""
