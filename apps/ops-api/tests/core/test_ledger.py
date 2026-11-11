import logging
from collections.abc import AsyncIterator
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.clients.ezcareer import Usage
from src.core.auth.models import User
from src.core.config import EzcareerSettings, ModelPrice
from src.core.stores import AgentModelCall, UsageLedger
from src.db import models  # noqa: F401
from src.db.base import Base
from src.db.session import create_session_factory


def _price(effective_from: date, input: str) -> ModelPrice:
    return ModelPrice(
        provider="claude",
        model="claude-sonnet-5-5",
        effective_from=effective_from,
        input_per_mtok=Decimal(input),
        output_per_mtok=Decimal(10),
        cache_read_per_mtok=Decimal("0.1"),
        cache_write_per_mtok=Decimal("2.5"),
    )


def _usage(model: str) -> Usage:
    return Usage(
        provider="claude",
        model=model,
        agent="career-director",
        node="model",
        input_tokens=1000,
        output_tokens=200,
        cache_read_tokens=600,
        cache_write_tokens=100,
        reasoning_tokens=50,
        latency_ms=1200,
        stop_reason="end_turn",
        request_id="msg_1",
    )


@pytest.fixture
async def factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield create_session_factory(engine)
    await engine.dispose()


async def test_a_call_costs_its_tokens_at_the_latest_price_already_in_force(
    factory: async_sessionmaker[AsyncSession],
):
    user_id = uuid4()
    async with factory() as session, session.begin():
        session.add(User(id=user_id, email="a@example.com"))
    prices = [
        _price(date(2020, 1, 1), "1"),
        _price(date(2021, 1, 1), "2"),
        _price(date(2999, 1, 1), "100"),
    ]

    await UsageLedger(factory, EzcareerSettings(prices=prices)).record(
        user_id, "u:c", "task-1", _usage("claude-sonnet-5-5")
    )

    async with factory() as session:
        [call] = (await session.scalars(select(AgentModelCall))).all()
    assert call.cost_micros == 300 * 2 + 600 * 0.1 + 100 * 2.5 + 200 * 10
    assert call.provider_request_id == "msg_1"


async def test_a_model_without_a_price_costs_nothing_and_warns_once(
    factory: async_sessionmaker[AsyncSession], caplog: pytest.LogCaptureFixture
):
    user_id = uuid4()
    async with factory() as session, session.begin():
        session.add(User(id=user_id, email="a@example.com"))
    ledger = UsageLedger(factory, EzcareerSettings())

    with caplog.at_level(logging.WARNING):
        for _ in range(2):
            await ledger.record(user_id, "u:c", "task-1", _usage("claude-x"))

    async with factory() as session:
        costs = (await session.scalars(select(AgentModelCall.cost_micros))).all()
    assert costs == [0, 0]
    assert [r.getMessage() for r in caplog.records] == [
        "No price for claude claude-x; costing it 0"
    ]
