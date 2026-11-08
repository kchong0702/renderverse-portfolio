from deepagents import DeepAgentState

from src.shared.profile import ProfileFact


class ProfileState(DeepAgentState):
    facts: list[ProfileFact]
    """The user's profile facts, which read_profile_facts lists"""
