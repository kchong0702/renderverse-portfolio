from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class FetchError(BaseModel):
    error: str
    """Why ops-api cannot answer, such as No such document"""


@dataclass(frozen=True)
class DataRequestKind[R: BaseModel]:
    request: type[R]
    """The model a request of this kind parses into"""

    answer: Callable[[UUID, R], Awaitable[BaseModel]]
    """Answers a parsed request for its user"""


type DataRequestKinds = Mapping[str, DataRequestKind[Any]]
"""Each fetch kind a feature answers, by name"""
