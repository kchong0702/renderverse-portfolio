from operator import or_
from typing import Annotated, NotRequired

from document_schema import AnyDocument
from langchain.agents import AgentState

from src.agents.career_director.types import DocumentContent
from src.agents.state import ProfileState
from src.shared.extraction.types import Line
from src.shared.profile import Preferences, ProfileFact


class CareerDirectorState(ProfileState):
    preferences: Preferences
    """What the user wants from a job"""

    document_contents: NotRequired[Annotated[dict[str, DocumentContent], or_]]
    """The content of each best match find_documents found this turn, by id, which
    handoff_to_child hands to career-consultant"""


class CareerDirectorHandoffState(AgentState):
    profile_facts: list[ProfileFact]
    """The user's profile facts, which every agent reads"""

    preferences: Preferences
    """What the user wants from a job"""

    active_agent: NotRequired[str]
    """The agent the conversation is with; a new turn goes to it"""

    document_id: NotRequired[str]
    """The document career-consultant works on, set when a handoff names one"""

    document: NotRequired[AnyDocument]
    """That document as it was when it was handed to career-consultant"""

    pdf_lines: NotRequired[list[Line]]
    """That document's uploaded PDF lines"""
