from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.features.draft_reply.checks import check_slots

CHECKS = {"slots": check_slots}
"""Every check the draft-reply configurations.yaml may turn on, by name"""


class DraftReplyConfigurations(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    checks: list[Literal["slots"]]
    """Checks run on each answer; errors go back to the agent"""

    max_free_slots: int = Field(gt=0)
    """Most free slots shown to the agent, the earliest first"""

    recursion_limit: int = Field(gt=0)
    """Most steps the run, and each agent turn within it, may take"""
