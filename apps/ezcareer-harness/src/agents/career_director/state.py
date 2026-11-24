from operator import or_
from typing import Annotated, NotRequired

from deepagents.middleware.filesystem import FilesystemState
from deepagents.middleware.summarization import SummarizationEvent
from document_schema import AnyDocument

from src.agents.career_director.types import DocumentContent
from src.agents.state import ProfileState
from src.shared.extraction.types import Line
from src.shared.profile import Preferences, ProfileFact


class CareerDirectorState(ProfileState):
    preferences: Preferences
    """What the user wants from a job"""

    document_contents: NotRequired[Annotated[dict[str, DocumentContent], or_]]
    """The content of each best match find_documents found this turn, by id, which
    handoff_document hands to career-consultant"""

    document_id: NotRequired[str]
    """The document career-consultant works on, which the graph keeps"""


class CareerDirectorHandoffState(FilesystemState):
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

    _summarization_event: NotRequired[SummarizationEvent]
    """The summary of the older messages the agent answering last made"""

    _summarization_session_id: NotRequired[str]
    """Names the file in files the summarised messages were moved to"""
