from __future__ import annotations

from datetime import time
from typing import Literal
from zoneinfo import available_timezones

from pydantic import BaseModel, Field, SecretStr, field_validator

from src.clients.ezcareer import ModelChoice

ConnectionId = Literal["google", "jsearch", "portfolio_site"]
"""An outside service Ops connects to"""

ConnectionStatus = Literal[
    "connected", "needs_reconnect", "not_connected", "not_configured"
]
"""Whether it works; needs_reconnect lacks a scope, not_configured lacks server keys"""


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

    timezone: str | None
    """IANA time zone the work hours are in, such as Asia/Kuala_Lumpur; None until the
    user chooses one"""


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
    automation: Automation
    """What agents do without being asked"""

    scheduling: Scheduling
    """Work hours and gaps for booking meetings"""

    ai_model: ModelChoice | None
    """The model the assistant and agents use; None leaves it to ezcareer-harness"""

    connections: list[Connection]
    """Every outside service and whether it is connected"""


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

    timezone: str | None = Field(default=None, max_length=64)
    """New IANA time zone; left out leaves it unchanged, and null is refused"""

    @field_validator("timezone")
    @classmethod
    def _must_be_iana(cls, value: str | None) -> str | None:
        """The time zone sent, refused unless it is an IANA name"""
        if value not in available_timezones():
            raise ValueError(f"{value} is not an IANA time zone")
        return value


class SettingsUpdate(BaseModel):
    """Only the fields sent are changed"""

    automation: AutomationUpdate | None = None
    """Changes to the automation rules"""

    scheduling: SchedulingUpdate | None = None
    """Changes to work hours and meeting gaps"""

    ai_model: ModelChoice | None = None
    """New model, checked against ezcareer-harness; null goes back to the harness default"""


__all__ = [
    "Automation",
    "Connection",
    "JSearchKey",
    "Scheduling",
    "SearchQuota",
    "SettingsRead",
    "SettingsUpdate",
]
