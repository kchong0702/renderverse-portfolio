from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.features.find_jobs.checks import check_ranked_jobs

CHECKS = {"ranked_jobs": check_ranked_jobs}
"""Every check the find-jobs profile.yaml may turn on, by name"""


class FindJobsProfile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    checks: list[Literal["ranked_jobs"]]
    """Checks run on each answer; errors go back to the agent"""

    recursion_limit: int = Field(gt=0)
    """Graph steps a run may take across all check rounds"""

    agent_recursion_limit: int = Field(gt=0)
    """Steps one agent turn may take"""
