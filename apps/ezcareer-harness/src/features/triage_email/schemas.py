from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from src.features.triage_email.enums import InterviewFormat, ThreadState


class Application(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: str
    """The application's id in ops"""

    company: str
    """The employer applied to"""

    role: str
    """The job applied for"""


class Interview(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    start: datetime
    """When it starts, with its offset"""

    end: datetime | None = None
    """When it ends, if the email says"""

    format: InterviewFormat | None = None
    """Video, phone or on site, if the email says"""

    location: str | None = None
    """The address or call link, if the email gives one"""


class EmailReading(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    state: ThreadState
    """What the thread asks of the user"""

    decide_by: date | None = None
    """For an offer, the date the user must answer by, if the email names one"""

    interview: Interview | None = None
    """For a confirmed interview, when and where it is"""
