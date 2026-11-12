from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImportProfileConfigurations(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    checks: list[Literal["verbatim"]]
    """Checks run on each reply; errors go back to the LLM"""

    recursion_limit: int = Field(gt=0)
    """Graph steps a run may take across all check rounds"""
