from pydantic import BaseModel, ConfigDict, Field

from src.shared.profile import Preferences, ProfileFact


class JobFinderInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    facts: list[ProfileFact] = Field(default_factory=list)
    """The user's profile facts"""

    preferences: Preferences = Field(default_factory=Preferences)
    """What the user wants from a job"""
