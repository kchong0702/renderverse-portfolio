from typing import Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from structlog.testing import capture_logs

from src.clients.ezcareer import ToolRequest
from src.core.agent_runner import Tool, ToolError, ToolExecutor, WriteTool
from src.core.auth.models import User


class _ShelfRequest(BaseModel):
    execute_tool: Literal["shelf"]
    size: int = Field(ge=1)


class _BookRequest(BaseModel):
    execute_tool: Literal["book"]
    title: str


class _Shelf(BaseModel):
    books: list[str]


class _Book(BaseModel):
    title: str


class _Library:
    def __init__(self):
        self.asked: list[tuple[UUID, BaseModel]] = []

    async def shelf(self, user_id: UUID, request: _ShelfRequest) -> _Shelf:
        """The first books of the user's shelf"""
        self.asked.append((user_id, request))
        return _Shelf(books=["Dune", "Emma"][: request.size])

    async def book(self, user_id: UUID, request: _BookRequest) -> _Book:
        """One of the user's books"""
        self.asked.append((user_id, request))
        return _Book(title=request.title)


class _SignUpRequest(BaseModel):
    execute_tool: Literal["sign_up"]
    email: str


class _SignedUp(BaseModel):
    email: str


async def _sign_up(
    session: AsyncSession, user_id: UUID, request: _SignUpRequest
) -> _SignedUp | ToolError:
    """Add a user, refusing an address without an @ after adding it"""
    session.add(User(email=request.email))
    await session.flush()
    if "@" not in request.email:
        return ToolError(error="Not an email")
    return _SignedUp(email=request.email)


def _executor(
    library: _Library, factory: async_sessionmaker[AsyncSession]
) -> ToolExecutor:
    """An executor over three features' tools, one each"""
    return ToolExecutor(
        [
            {"shelf": Tool(_ShelfRequest, library.shelf)},
            {"book": Tool(_BookRequest, library.book)},
            {"sign_up": WriteTool(_SignUpRequest, _sign_up)},
        ],
        factory,
    )


async def _emails(factory: async_sessionmaker[AsyncSession]) -> list[str]:
    async with factory() as session:
        return list(await session.scalars(select(User.email).order_by(User.email)))


async def test_each_tool_is_executed_by_its_feature_for_the_user(factory):
    library = _Library()
    user_id = uuid4()
    executor = _executor(library, factory)

    shelf = await executor.execute(
        user_id, "task-1", "i-1", ToolRequest(execute_tool="shelf", size=1)
    )
    book = await executor.execute(
        user_id, "task-1", "i-2", ToolRequest(execute_tool="book", title="Emma")
    )

    assert (shelf, book) == (_Shelf(books=["Dune"]), _Book(title="Emma"))
    assert library.asked == [
        (user_id, _ShelfRequest(execute_tool="shelf", size=1)),
        (user_id, _BookRequest(execute_tool="book", title="Emma")),
    ]


def test_two_features_with_the_same_tool_are_refused(factory):
    library = _Library()

    with pytest.raises(ValueError, match=r"registered twice: \['book'\]"):
        ToolExecutor(
            [
                {"shelf": Tool(_ShelfRequest, library.shelf)},
                {"book": Tool(_BookRequest, library.book)},
                {"book": Tool(_BookRequest, library.book)},
            ],
            factory,
        )


async def test_a_tool_no_feature_has_is_refused_with_why(factory):
    library = _Library()

    result = await _executor(library, factory).execute(
        uuid4(), "task-1", "i-1", ToolRequest(execute_tool="weather")
    )

    assert result == ToolError(error="Ops has no weather tool")
    assert library.asked == []


async def test_a_malformed_request_is_refused_with_why_without_running_its_feature(
    factory,
):
    library = _Library()

    result = await _executor(library, factory).execute(
        uuid4(), "task-1", "i-1", ToolRequest(execute_tool="shelf", size=0)
    )

    assert isinstance(result, ToolError)
    assert "size" in result.error
    assert "greater than or equal to 1" in result.error
    assert library.asked == []


async def test_each_execution_logs_its_tool_user_and_outcome_but_no_arguments(
    factory,
):
    user_id = uuid4()
    executor = _executor(_Library(), factory)

    with capture_logs() as logs:
        await executor.execute(
            user_id, "t", "i-1", ToolRequest(execute_tool="book", title="Secret diary")
        )
        await executor.execute(
            user_id, "t", "i-2", ToolRequest(execute_tool="shelf", size=0)
        )
        await executor.execute(
            user_id, "t", "i-3", ToolRequest(execute_tool="weather", city="Ipoh")
        )

    assert [
        (log["event"], log["tool"], log["user_id"], log["outcome"]) for log in logs
    ] == [
        ("tool_execution", "book", str(user_id), "executed"),
        ("tool_execution", "shelf", str(user_id), "malformed"),
        ("tool_execution", "weather", str(user_id), "unknown"),
    ]
    assert "Secret diary" not in str(logs)
    assert "Ipoh" not in str(logs)


async def test_a_write_asked_again_by_its_interrupt_returns_its_first_result(factory):
    executor = _executor(_Library(), factory)
    request = ToolRequest(execute_tool="sign_up", email="ana@example.com")

    with capture_logs() as logs:
        first = await executor.execute(uuid4(), "task-1", "i-1", request)
        again = await executor.execute(uuid4(), "task-1", "i-1", request)

    assert first == _SignedUp(email="ana@example.com")
    assert again.model_dump() == first.model_dump()
    assert await _emails(factory) == ["ana@example.com"]
    assert [log["outcome"] for log in logs] == ["executed", "repeated"]


async def test_a_refused_write_is_rolled_back_and_not_kept(factory):
    executor = _executor(_Library(), factory)
    request = ToolRequest(execute_tool="sign_up", email="not-an-email")

    first = await executor.execute(uuid4(), "task-1", "i-1", request)
    again = await executor.execute(uuid4(), "task-1", "i-1", request)

    assert first == again == ToolError(error="Not an email")
    assert await _emails(factory) == []


async def test_a_write_runs_again_once_its_tasks_results_are_forgotten(factory):
    executor = _executor(_Library(), factory)

    await executor.execute(
        uuid4(), "task-1", "i-1", ToolRequest(execute_tool="sign_up", email="a@x.io")
    )
    await executor.forget("task-1")
    await executor.execute(
        uuid4(), "task-1", "i-1", ToolRequest(execute_tool="sign_up", email="b@x.io")
    )

    assert await _emails(factory) == ["a@x.io", "b@x.io"]
