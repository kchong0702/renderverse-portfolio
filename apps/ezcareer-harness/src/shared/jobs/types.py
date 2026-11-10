from datetime import datetime

from pydantic import BaseModel, ConfigDict

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
    """JSearch job id"""

    title: str
    """Job title"""

    company: str
    """Employer name"""

    location: str
    """City and country, as JSearch gives them"""

    country: CountryCode | None
    """Country the job is in, if JSearch gives one"""

    remote: bool
    """Whether the job is remote"""

    posted_at: datetime | None
    """When the job was posted, if known"""

    apply_url: str
    """Where to apply"""

    lines: list[PostingLine]
    """The description, numbered from 1; untrusted"""
