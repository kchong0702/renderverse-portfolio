from pydantic import BaseModel, ConfigDict, Field

from src.shared.profile.preferences import Preferences
from src.shared.profile.profile_fact import ProfileFact


class Profile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    facts: list[ProfileFact]
    """What the user has done and knows"""

    preferences: Preferences = Field(default_factory=Preferences)
    """What the user wants from a job"""
