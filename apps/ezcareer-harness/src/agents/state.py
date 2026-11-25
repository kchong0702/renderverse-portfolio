from deepagents import DeepAgentState

from src.shared.profile import ProfileFact


class ProfileState(DeepAgentState):
    profile_facts: list[ProfileFact]
    """The user's profile facts"""
