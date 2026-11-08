from src.agents.state import ProfileState
from src.shared.profile import Preferences


class JobFinderState(ProfileState):
    preferences: Preferences
    """What the user wants from a job"""
