from __future__ import annotations

from datetime import time
from typing import Literal

from pydantic import BaseModel, Field

AiProvider = Literal["claude", "openai", "glm"]
"""The model the assistant and agents use"""

ConnectionId = Literal["google", "jsearch", "portfolio_site"]
"""An outside service Ops connects to"""

ConnectionStatus = Literal["connected", "not_connected"]
"""Whether a connection is set up"""


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


class Scheduling(BaseModel):
    work_day_start: time
    """Earliest time meetings are offered"""

    work_day_end: time
    """Latest time meetings may end; must be after work_day_start"""

    meeting_gap_minutes: int = Field(ge=0, le=240)
    """Free minutes kept between meetings"""


class Connection(BaseModel):
    id: ConnectionId
    """Which service"""

    status: ConnectionStatus
    """Whether it is connected"""


class SettingsRead(BaseModel):
    job_agent: JobAgent
    """The daily job search"""

    automation: Automation
    """What agents do without being asked"""

    scheduling: Scheduling
    """Work hours and gaps for booking meetings"""

    ai_provider: AiProvider
    """The model the assistant and agents use"""

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

    ai_provider: AiProvider | None = None
    """New model; None leaves it unchanged"""


__all__ = [
    "AiProvider",
    "Automation",
    "Connection",
    "JobAgent",
    "Scheduling",
    "SettingsRead",
    "SettingsUpdate",
]
