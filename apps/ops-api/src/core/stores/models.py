from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.stores.enums import AgentRunStatus
from src.db.base import Base, EnumString, utcnow
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin


class AgentRun(UserScopedMixin, AuditMixin, Base):
    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    """The run's id"""

    thread_id: Mapped[str] = mapped_column(String(200), index=True)
    """The A2A context_id the run belongs to, such as a user's chat"""

    agent: Mapped[str] = mapped_column(String(100))
    """The harness agent or workflow the run calls"""

    task_id: Mapped[str | None] = mapped_column(String(100))
    """The A2A task the run started or resumed; None until it starts"""

    status: Mapped[AgentRunStatus] = mapped_column(EnumString(AgentRunStatus))
    """Where the run stands"""

    active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    """When the run last started or added an event"""

    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """When the run ended; None while it runs"""


class AgentEvent(UserScopedMixin, AuditMixin, Base):
    __tablename__ = "agent_events"

    run_id: Mapped[str] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="CASCADE"), primary_key=True
    )
    """The run the event belongs to"""

    seq: Mapped[int] = mapped_column(primary_key=True)
    """The event's number in its run, from 1"""

    data: Mapped[dict[str, Any]]
    """The event"""


class AgentModelCall(IdMixin, UserScopedMixin, AuditMixin, Base):
    """One model call's usage and cost; kept when its thread's runs are deleted"""

    __tablename__ = "agent_model_calls"
    __table_args__ = (
        Index("ix_agent_model_calls_user_id_created_at", "user_id", "created_at"),
    )

    thread_id: Mapped[str] = mapped_column(String(200))
    """The A2A context_id the call ran in"""

    task_id: Mapped[str] = mapped_column(String(100))
    """The A2A task the call ran in, which agent_runs.task_id names"""

    agent: Mapped[str] = mapped_column(String(100))
    """The harness agent whose model made the call"""

    node: Mapped[str] = mapped_column(String(100))
    """The graph node that made the call"""

    provider: Mapped[str] = mapped_column(String(20))
    """The model's family, such as claude"""

    model: Mapped[str] = mapped_column(String(100))
    """The model the call asked for"""

    input_tokens: Mapped[int]
    """Input tokens, cache reads and writes included"""

    output_tokens: Mapped[int]
    """Output tokens, reasoning included"""

    cache_read_tokens: Mapped[int]
    """Input tokens read from the prompt cache"""

    cache_write_tokens: Mapped[int]
    """Input tokens written to the prompt cache"""

    reasoning_tokens: Mapped[int]
    """Output tokens spent reasoning"""

    cost_micros: Mapped[int] = mapped_column(BigInteger)
    """The call's cost in millionths of a USD, at the price in force when it ran"""

    latency_ms: Mapped[int]
    """How long the call took"""

    stop_reason: Mapped[str | None] = mapped_column(String(50))
    """Why the provider stopped, such as end_turn"""

    provider_request_id: Mapped[str | None] = mapped_column(String(200))
    """The provider's id for the response, when it gave one"""


__all__ = ["AgentEvent", "AgentModelCall", "AgentRun"]
