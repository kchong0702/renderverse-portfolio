from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WriteNetworkingConfigurations(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    checks: list[Literal["coverage", "citations", "form"]]
    """Checks run on each answer"""

    max_headline_chars: int = Field(gt=0)
    """Most characters the headline may have"""

    max_summary_chars: int = Field(gt=0)
    """Most characters the summary may have"""

    max_description_chars: int = Field(gt=0)
    """Most characters each description may have"""

    recursion_limit: int = Field(gt=0)
    """Most steps the run, and each agent turn within it, may take"""
