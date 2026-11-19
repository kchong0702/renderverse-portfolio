from typing import NotRequired

from langchain.agents import AgentState

from src.agents.state import ProfileState
from src.shared.profile import Preferences, ProfileFact


class CareerDirectorState(ProfileState):
    preferences: Preferences
    """What the user wants from a job"""


class CareerDirectorHandoffState(AgentState):
    facts: list[ProfileFact]
    """The user's profile facts, which every agent reads"""

    preferences: Preferences
    """What the user wants from a job"""

    active_agent: NotRequired[str]
    """The agent the conversation is with; a new turn goes to it"""

    document_id: NotRequired[str]
    """The document career-consultant works on, set when the conversation is handed
    to it"""
