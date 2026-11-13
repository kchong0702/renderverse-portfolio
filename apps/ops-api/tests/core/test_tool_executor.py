from typing import Literal
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field
from structlog.testing import capture_logs

from src.clients.ezcareer import ToolRequest
from src.core.runner import Tool, ToolError, ToolExecutor


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


def _executor(library: _Library) -> ToolExecutor:
    """An executor over two features' tools, one each"""
    return ToolExecutor(
        {"shelf": Tool(_ShelfRequest, library.shelf)},
        {"book": Tool(_BookRequest, library.book)},
    )


async def test_each_tool_is_executed_by_its_feature_for_the_user():
    library = _Library()
    user_id = uuid4()
    execute = _executor(library).for_user(user_id)

    shelf = await execute(ToolRequest(execute_tool="shelf", size=1))
    book = await execute(ToolRequest(execute_tool="book", title="Emma"))

    assert (shelf, book) == (_Shelf(books=["Dune"]), _Book(title="Emma"))
    assert library.asked == [
        (user_id, _ShelfRequest(execute_tool="shelf", size=1)),
        (user_id, _BookRequest(execute_tool="book", title="Emma")),
    ]


def test_two_features_with_the_same_tool_are_refused():
    library = _Library()

    with pytest.raises(ValueError, match=r"registered twice: \['book'\]"):
        ToolExecutor(
            {"shelf": Tool(_ShelfRequest, library.shelf)},
            {"book": Tool(_BookRequest, library.book)},
            {"book": Tool(_BookRequest, library.book)},
        )


async def test_a_tool_no_feature_has_is_refused_with_why():
    library = _Library()

    result = await _executor(library).for_user(uuid4())(
        ToolRequest(execute_tool="weather")
    )

    assert result == ToolError(error="Ops has no weather tool")
    assert library.asked == []


async def test_a_malformed_request_is_refused_with_why_without_running_its_feature():
    library = _Library()

    result = await _executor(library).for_user(uuid4())(
        ToolRequest(execute_tool="shelf", size=0)
    )

    assert isinstance(result, ToolError)
    assert "size" in result.error
    assert "greater than or equal to 1" in result.error
    assert library.asked == []


async def test_each_execution_logs_its_tool_user_and_outcome_but_no_arguments():
    user_id = uuid4()
    execute = _executor(_Library()).for_user(user_id)

    with capture_logs() as logs:
        await execute(ToolRequest(execute_tool="book", title="Secret diary"))
        await execute(ToolRequest(execute_tool="shelf", size=0))
        await execute(ToolRequest(execute_tool="weather", city="Ipoh"))

    assert [
        (log["event"], log["tool"], log["user_id"], log["outcome"]) for log in logs
    ] == [
        ("tool_execution", "book", str(user_id), "executed"),
        ("tool_execution", "shelf", str(user_id), "malformed"),
        ("tool_execution", "weather", str(user_id), "unknown"),
    ]
    assert "Secret diary" not in str(logs)
    assert "Ipoh" not in str(logs)
