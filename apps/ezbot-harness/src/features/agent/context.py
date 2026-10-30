from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class EzbotContext(BaseModel):
    model_config = ConfigDict(frozen=True)

    today: date
    """Current UTC date, so the bot can reason about time"""


__all__ = ["EzbotContext"]
