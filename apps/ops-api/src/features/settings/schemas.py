from __future__ import annotations

from datetime import time
from typing import Literal

from pydantic import BaseModel, Field, SecretStr

from src.clients.ezcareer import ModelChoice

ConnectionId = Literal["google", "jsearch", "portfolio_site"]
"""An outside service Ops connects to"""

ConnectionStatus = Literal["connected", "not_connected", "not_configured"]
"""Whether a connection is set up; not_configured when the server lacks its keys"""


class JobAgent(BaseModel):
    query: str = Field(max_length=200)
    """What the daily run searches for, e.g. "Backend engineer, Python\""""

    location: str = Field(max_length=200)
    """Where the postings should be, e.g. "Kuala Lumpur or remote\""""

    run_at: time
    """When the daily run starts"""

    min_score: int = Field(ge=0, le=100)
    """Postings scoring below this are dropped"""


class Automation(BaseModel):
    tailor_strong_matches: bool
    """Draft a tailored résumé for new picks scoring 85 or more"""

    follow_up_reminders: bool
    """Remind after 7 days without a reply and draft the email"""

    suggest_replies: bool
    """Read employer replies and suggest an answer"""

    add_interview_invites: bool
    """Add each interview an email confirms to Google Calendar"""

    offer_free_slots: bool
    """Offer free calendar slots in a suggested reply"""


class Scheduling(BaseModel):
    work_day_start: time
    """Earliest time meetings are offered"""

    work_day_end: time
    """Latest time meetings may end; must be after work_day_start"""

    meeting_gap_minutes: int = Field(ge=0, le=240)
    """Free minutes kept between meetings"""


class SearchQuota(BaseModel):
    remaining: int
    """Searches left on the JSearch key this period"""

    limit: int
    """Searches the JSearch key allows each period"""


class Connection(BaseModel):
    id: ConnectionId
    """Which service"""

    status: ConnectionStatus
    """Whether it is connected"""

    quota: SearchQuota | None = None
    """JSearch's searches left, from the last find run; None when not known"""

    account: str | None = None
    """The connected account, such as the Gmail address; None when not connected"""


class JSearchKey(BaseModel):
    api_key: SecretStr = Field(min_length=1)
    """The user's RapidAPI key for JSearch; unbounded, so a 422 never echoes it"""


class SettingsRead(BaseModel):
    job_agent: JobAgent
    """The daily job search"""

    automation: Automation
    """What agents do without being asked"""

    scheduling: Scheduling
    """Work hours and gaps for booking meetings"""

    ai_model: ModelChoice | None
    """The model the assistant and agents use; None leaves it to ezcareer-harness"""

    connections: list[Connection]
    """Every outside service and whether it is connected"""


class JobAgentUpdate(BaseModel):
    query: str | None = Field(default=None, max_length=200)
    """New search; None leaves it unchanged"""

    location: str | None = Field(default=None, max_length=200)
    """New location; None leaves it unchanged"""

    run_at: time | None = None
    """New daily run time; None leaves it unchanged"""

    min_score: int | None = Field(default=None, ge=0, le=100)
    """New minimum score; None leaves it unchanged"""


class AutomationUpdate(BaseModel):
    tailor_strong_matches: bool | None = None
    """Turn tailored résumé drafts on or off; None leaves it unchanged"""

    follow_up_reminders: bool | None = None
    """Turn follow-up reminders on or off; None leaves it unchanged"""

    suggest_replies: bool | None = None
    """Turn suggested replies on or off; None leaves it unchanged"""

    add_interview_invites: bool | None = None
    """Turn adding interviews to the calendar on or off; None leaves it unchanged"""

    offer_free_slots: bool | None = None
    """Turn offering free slots on or off; None leaves it unchanged"""


class SchedulingUpdate(BaseModel):
    work_day_start: time | None = None
    """New start of the work day; None leaves it unchanged"""

    work_day_end: time | None = None
    """New end of the work day; None leaves it unchanged"""

    meeting_gap_minutes: int | None = Field(default=None, ge=0, le=240)
    """New gap between meetings; None leaves it unchanged"""


class SettingsUpdate(BaseModel):
    """Only the fields sent are changed"""

    job_agent: JobAgentUpdate | None = None
    """Changes to the daily job search"""

    automation: AutomationUpdate | None = None
    """Changes to the automation rules"""

    scheduling: SchedulingUpdate | None = None
    """Changes to work hours and meeting gaps"""

    ai_model: ModelChoice | None = None
    """New model, checked against ezcareer-harness; None leaves it unchanged"""


__all__ = [
    "Automation",
    "Connection",
    "JSearchKey",
    "JobAgent",
    "Scheduling",
    "SearchQuota",
    "SettingsRead",
    "SettingsUpdate",
]
