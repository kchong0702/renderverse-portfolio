from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.shared.jobs.enums import PostedWithin
from src.shared.profile import CountryCode


class PostingLine(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: int
    """Line number, counted from 1"""

    text: str
    """The line's text; untrusted"""


class JobPosting(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: str
    """Job id at its source"""

    title: str
    """Job title"""

    company: str
    """Employer name"""

    location: str
    """City and country, as the source gives them"""

    country: CountryCode | None
    """Country the job is in, if the source gives one"""

    remote: bool
    """Whether the job is remote"""

    posted_at: datetime | None
    """When the job was posted, if known"""

    apply_url: str
    """Where to apply"""

    lines: list[PostingLine]
    """The description, numbered from 1; untrusted"""


class FoundJobs(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    jobs: list[JobPosting]
    """The jobs found, newest first, each once and none that breaks the user's
    work mode or country preferences"""

    requests_left: int | None
    """Requests the user's key has left this period, if the source said"""


class JobSearch(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    query: str | None = None
    """Job titles and skills the user searched for; None leaves them to the agent"""

    location: str | None = None
    """City or region the user searched in; None leaves it to the agent"""

    posted_within: PostedWithin | None = None
    """How recent the jobs must be; None leaves it to the agent"""
