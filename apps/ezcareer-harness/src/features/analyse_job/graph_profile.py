from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.features.analyse_job.checks import check_citations

CHECKS = {"citations": check_citations}
"""Every check the analyse profile.yaml may turn on, by name"""


class AnalyseJobProfile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    checks: list[Literal["citations"]]
    """Checks run on each answer; errors go back to the agent"""

    recursion_limit: int = Field(gt=0)
    """Graph steps a run may take across all check rounds"""

    agent_recursion_limit: int = Field(gt=0)
    """Steps one agent turn may take"""
