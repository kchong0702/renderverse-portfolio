import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.ezcareer import Usage
from src.core.config import EzcareerSettings
from src.core.stores.models import AgentModelCall
from src.db.base import utcnow

_log = logging.getLogger(__name__)


class UsageLedger:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: EzcareerSettings,
    ):
        """Keep one row per model call, priced from settings.prices"""
        self._factory = session_factory
        """Sessions for writing calls"""

        self._prices = settings.prices
        """Each model's prices over time"""

        self._unpriced: set[tuple[str, str]] = set()
        """Models already warned about having no price"""

    async def record(
        self, user_id: UUID, thread_id: str, task_id: str, usage: Usage
    ) -> None:
        """Keep the user's model call with its cost at the price in force now; 0 when
        the model has none"""
        today = utcnow().date()
        price = max(
            (
                p
                for p in self._prices
                if p.provider == usage.provider
                and p.model == usage.model
                and p.effective_from <= today
            ),
            key=lambda p: p.effective_from,
            default=None,
        )
        if price is None and (usage.provider, usage.model) not in self._unpriced:
            self._unpriced.add((usage.provider, usage.model))
            _log.warning(
                "No price for %s %s; costing it 0", usage.provider, usage.model
            )
        async with self._factory() as session, session.begin():
            session.add(
                AgentModelCall(
                    user_id=user_id,
                    thread_id=thread_id,
                    task_id=task_id,
                    agent=usage.agent,
                    node=usage.node,
                    provider=usage.provider,
                    model=usage.model,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cache_read_tokens=usage.cache_read_tokens,
                    cache_write_tokens=usage.cache_write_tokens,
                    reasoning_tokens=usage.reasoning_tokens,
                    cost_micros=0
                    if price is None
                    else round(
                        price.input_per_mtok
                        * (
                            usage.input_tokens
                            - usage.cache_read_tokens
                            - usage.cache_write_tokens
                        )
                        + price.cache_read_per_mtok * usage.cache_read_tokens
                        + price.cache_write_per_mtok * usage.cache_write_tokens
                        + price.output_per_mtok * usage.output_tokens
                    ),
                    latency_ms=usage.latency_ms,
                    stop_reason=usage.stop_reason,
                    provider_request_id=usage.request_id,
                )
            )


__all__ = ["UsageLedger"]
