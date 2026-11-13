from pydantic import BaseModel, ConfigDict, Field, computed_field

from src.features.analyse_job import Requirement, fit_score
from src.shared.jobs import JobPosting


class RankedJob(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    job_id: str
    """A job's id as search_jobs showed it, such as job-3f9a1c2e"""

    requirements: list[Requirement] = Field(min_length=1)
    """Every requirement in the description, mapped to the profile"""


class RankedJobs(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    jobs: list[RankedJob]
    """Up to 10 jobs search_jobs returned, best fit first"""


class MatchedJob(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    posting: JobPosting
    """The job as search_jobs returned it"""

    requirements: list[Requirement]
    """The agent's mapping of its requirements"""

    @computed_field
    @property
    def fit(self) -> int:
        """Fit score from 0 to 100, computed from the requirements"""
        return fit_score(self.requirements)
