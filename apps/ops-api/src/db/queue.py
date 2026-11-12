from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, and_, or_, select, true, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, aliased

from src.db.base import utcnow

MAX_ATTEMPTS = 3
"""How many times a row is tried before it fails"""

RETRY_SECONDS = 30
"""The wait before the second attempt, doubling for each one after"""


class Claimable(Protocol):
    id: Mapped[UUID]
    """The row's id"""

    status: Mapped[StrEnum]
    """How far the row has got"""

    claim_token: Mapped[UUID | None]
    """The claim of the worker processing it"""

    lease_until: Mapped[datetime | None]
    """When the claim lapses unless the worker extends it"""

    attempts: Mapped[int]
    """How many times it has been claimed"""

    run_after: Mapped[datetime]
    """The earliest a worker may claim it"""

    error: Mapped[str]
    """Why the last attempt failed; empty otherwise"""

    finished_at: Mapped[datetime | None]
    """When it ended"""

    created_at: Mapped[datetime]
    """When it was queued"""


@dataclass(frozen=True)
class Queue[R: Claimable]:
    model: type[R]
    """The table whose rows workers claim"""

    queued: StrEnum
    """The status of a row waiting for a worker"""

    running: StrEnum
    """The status of a row a worker holds under its claim token until lease_until"""

    done: StrEnum
    """The status of a row processed, with its results written"""

    failed: StrEnum
    """The status of a row given up after its last attempt"""

    lapsed: str
    """The error of a row whose last attempt's worker stopped extending its lease"""

    abandoned: StrEnum | None = None
    """The status of a row cancelled while a worker held it, so the worker drops it;
    None for a queue without one"""

    eligible: Callable[[type[R], datetime], ColumnElement[bool]] = lambda due, now: (
        true()
    )
    """Which rows due now may be claimed, beyond their status and time"""


async def fail_lapsed[R: Claimable](session: AsyncSession, queue: Queue[R]) -> int:
    """Fail every row whose worker stopped extending its lease on its last attempt,
    releasing its claim; how many"""
    model = queue.model
    now = utcnow()
    lapsed = (
        select(model.id)
        .where(
            model.status == queue.running,
            model.lease_until < now,
            model.attempts >= MAX_ATTEMPTS,
        )
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    result = await session.execute(
        update(model)
        .where(model.id.in_(lapsed))
        .values(
            status=queue.failed,
            claim_token=None,
            lease_until=None,
            error=queue.lapsed,
            finished_at=now,
        )
    )
    return result.rowcount


async def claim[R: Claimable](
    session: AsyncSession, queue: Queue[R], lease: timedelta
) -> R | None:
    """The next row due, claimed under a fresh token and lease; None when none is due
    or another worker took it first"""
    model = queue.model
    now = utcnow()
    due = aliased(model)
    next_due = (
        select(due.id)
        .where(
            or_(
                and_(due.status == queue.queued, due.run_after <= now),
                and_(
                    due.status == queue.running,
                    due.lease_until < now,
                    due.attempts < MAX_ATTEMPTS,
                ),
            ),
            queue.eligible(due, now),
        )
        .order_by(due.run_after, due.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    try:
        async with session.begin_nested():
            return await session.scalar(
                update(model)
                .where(model.id == next_due)
                .values(
                    status=queue.running,
                    claim_token=uuid4(),
                    lease_until=now + lease,
                    attempts=model.attempts + 1,
                )
                .returning(model)
            )
    except IntegrityError:
        return None


async def heartbeat[R: Claimable](
    session: AsyncSession,
    queue: Queue[R],
    row_id: UUID,
    claim_token: UUID,
    lease: timedelta,
) -> bool:
    """Extend the lease of a row still running under the claim; False once the claim
    was lost to another worker or the row was abandoned"""
    model = queue.model
    result = await session.execute(
        update(model)
        .where(
            model.id == row_id,
            model.claim_token == claim_token,
            model.status == queue.running,
        )
        .values(lease_until=utcnow() + lease)
    )
    if result.rowcount == 1:
        return True
    status = await session.scalar(
        select(model.status).where(model.id == row_id, model.claim_token == claim_token)
    )
    return status is not None and status is not queue.abandoned


async def complete[R: Claimable](
    session: AsyncSession, queue: Queue[R], row_id: UUID, claim_token: UUID
) -> R | None:
    """Mark a row still running under the claim done and return it; None when the
    claim was lost"""
    model = queue.model
    return await session.scalar(
        update(model)
        .where(
            model.id == row_id,
            model.claim_token == claim_token,
            model.status == queue.running,
        )
        .values(status=queue.done, finished_at=utcnow(), error="")
        .returning(model)
    )


async def fail[R: Claimable](
    session: AsyncSession,
    queue: Queue[R],
    row_id: UUID,
    claim_token: UUID,
    error: str,
    *,
    retry: bool,
) -> R | None:
    """Queue a row still running under the claim again after a backoff when retry is
    set and attempts are left, else fail it; None when the claim was lost"""
    model = queue.model
    row = await session.scalar(
        select(model)
        .where(
            model.id == row_id,
            model.claim_token == claim_token,
            model.status == queue.running,
        )
        .with_for_update(of=model)
    )
    if row is None:
        return None
    row.error = error
    if retry and row.attempts < MAX_ATTEMPTS:
        row.status = queue.queued
        row.run_after = utcnow() + timedelta(seconds=RETRY_SECONDS * 2**row.attempts)
    else:
        row.status = queue.failed
        row.finished_at = utcnow()
    await session.flush()
    return row


async def release[R: Claimable](
    session: AsyncSession, queue: Queue[R], row_id: UUID, claim_token: UUID
) -> bool:
    """Queue a row still running under the claim again at once, the attempt
    uncounted; False when the claim was lost"""
    model = queue.model
    result = await session.execute(
        update(model)
        .where(
            model.id == row_id,
            model.claim_token == claim_token,
            model.status == queue.running,
        )
        .values(
            status=queue.queued,
            claim_token=None,
            lease_until=None,
            attempts=model.attempts - 1,
        )
    )
    return result.rowcount == 1


__all__ = [
    "MAX_ATTEMPTS",
    "RETRY_SECONDS",
    "Claimable",
    "Queue",
    "claim",
    "complete",
    "fail",
    "fail_lapsed",
    "heartbeat",
    "release",
]
