from collections.abc import Iterable
from typing import Annotated, Protocol

from pydantic import StringConstraints

Id = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
"""Stable key among siblings"""

BlockId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
"""Id of a block"""

FileHash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
"""Sha256 of a file's bytes"""

DataFieldPath = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9_-]+(/[A-Za-z0-9_-]+)*$")
]
"""Ids from the root, such as blocks/exp/items/acme"""

Source = Annotated[
    str,
    StringConstraints(
        pattern=r"^(p\d+\.s\d+|fact:[A-Za-z0-9_-]+|user:.+|agent:[A-Za-z0-9_-]+)$"
    ),
]
"""Where text came from: a PDF line, a fact, the user or the agent"""


class HasId(Protocol):
    @property
    def id(self) -> str: ...


def require_unique_ids(items: Iterable[HasId], where: str) -> None:
    """Raises when two items share an id"""
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError(f"ids must be unique in {where}")
