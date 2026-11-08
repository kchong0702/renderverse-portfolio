from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.features.find_jobs.checks import check_ranked_jobs

CHECKS = {"ranked_jobs": check_ranked_jobs}
"""Every check the find-jobs configurations.yaml may turn on, by name"""


class FindJobsConfigurations(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    checks: list[Literal["ranked_jobs"]]
    """Checks run on each answer; errors go back to the agent"""

    recursion_limit: int = Field(gt=0)
    """Most steps the run, and each agent turn within it, may take"""
