from src.shared.models import Preferences
from src.shared.tools import ProfileState


class JobFinderState(ProfileState):
    preferences: Preferences
    """What the user wants from a job, which search_jobs filters by"""
