from typing import NotRequired

from deepagents import DeepAgentState
from deepagents.middleware.summarization import SummarizationEvent

from src.shared.profile import ProfileFact


class ProfileState(DeepAgentState):
    profile_facts: list[ProfileFact]
    """The user's profile facts"""

    _summarization_event: NotRequired[SummarizationEvent]
    """deepagents' summary of the older messages, public so an agent graph keeps it"""

    _summarization_session_id: NotRequired[str]
    """Names the file deepagents moves summarised messages to, kept the same way"""
