from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, utcnow
from src.db.mixins import UserScopedMixin


class AgentRun(UserScopedMixin, Base):
    """One agent run, such as an assistant turn, that any ops-api process can
    replay and follow"""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    """The run's id, the first half of each event id"""

    key: Mapped[str] = mapped_column(String(200), index=True)
    """What the run belongs to, such as a user's chat"""

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    """When the run started"""

    active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    """When the run last started or added an event"""

    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """When the run ended; None while it runs"""


class AgentEvent(UserScopedMixin, Base):
    __tablename__ = "agent_events"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), primary_key=True
    )
    """The run the event belongs to"""

    seq: Mapped[int] = mapped_column(primary_key=True)
    """The event's number in its run, from 1"""

    data: Mapped[str] = mapped_column(Text)
    """The event as JSON"""
