from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from structlog.testing import capture_logs

from src.clients.ezcareer import DataRequest
from src.core.data_requests import DataRequestDispatcher, DataRequestKind, FetchError


class _ShelfRequest(BaseModel):
    fetch: Literal["shelf"]
    size: int = Field(ge=1)


class _BookRequest(BaseModel):
    fetch: Literal["book"]
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


def _dispatcher(library: _Library) -> DataRequestDispatcher:
    """A dispatcher over two features' tables, one kind each"""
    return DataRequestDispatcher(
        {"shelf": DataRequestKind(_ShelfRequest, library.shelf)},
        {"book": DataRequestKind(_BookRequest, library.book)},
    )


async def test_each_kind_is_answered_by_its_feature_for_the_user():
    library = _Library()
    user_id = uuid4()
    answer = _dispatcher(library).for_user(user_id)

    shelf = await answer(DataRequest(fetch="shelf", size=1))
    book = await answer(DataRequest(fetch="book", title="Emma"))

    assert (shelf, book) == (_Shelf(books=["Dune"]), _Book(title="Emma"))
    assert library.asked == [
        (user_id, _ShelfRequest(fetch="shelf", size=1)),
        (user_id, _BookRequest(fetch="book", title="Emma")),
    ]


async def test_a_kind_no_feature_answers_is_answered_with_why():
    library = _Library()

    answer = await _dispatcher(library).for_user(uuid4())(DataRequest(fetch="weather"))

    assert answer == FetchError(error="Ops can't answer weather")
    assert library.asked == []


async def test_a_malformed_request_is_answered_with_why_without_asking_its_feature():
    library = _Library()

    answer = await _dispatcher(library).for_user(uuid4())(
        DataRequest(fetch="shelf", size=0)
    )

    assert isinstance(answer, FetchError)
    assert "size" in answer.error
    assert "greater than or equal to 1" in answer.error
    assert library.asked == []


async def test_each_request_logs_its_kind_user_and_outcome_but_no_arguments():
    user_id = uuid4()
    answer = _dispatcher(_Library()).for_user(user_id)

    with capture_logs() as logs:
        await answer(DataRequest(fetch="book", title="Secret diary"))
        await answer(DataRequest(fetch="shelf", size=0))
        await answer(DataRequest(fetch="weather", city="Ipoh"))

    assert [
        (log["event"], log["kind"], log["user_id"], log["outcome"]) for log in logs
    ] == [
        ("data_request", "book", str(user_id), "answered"),
        ("data_request", "shelf", str(user_id), "malformed"),
        ("data_request", "weather", str(user_id), "unknown"),
    ]
    assert "Secret diary" not in str(logs)
    assert "Ipoh" not in str(logs)
