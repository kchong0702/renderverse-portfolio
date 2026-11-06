import unicodedata
from collections.abc import Callable, Collection, Iterator, Sequence
from enum import StrEnum
from itertools import pairwise

from document_schema import RichValue, Value
from pydantic import BaseModel, ConfigDict, ValidationError

from src.shared.extraction import Line
from src.shared.models import ResumeImport


class Check(StrEnum):
    SCHEMA = "schema"
    """The reply is a valid ResumeImport; always runs"""

    VERBATIM = "verbatim"
    """Each value's text appears in the lines it cites"""

    COVERAGE = "coverage"
    """Each line is cited or skipped"""

    ORDER = "order"
    """Blocks follow the order of their lines"""


class CheckError(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    check: Check
    """The check that failed"""

    path: str
    """Where in the reply, such as content/blocks/experience/items/acme/role"""

    message: str
    """What is wrong, written for the LLM"""


def _normal(text: str) -> str:
    """Folds case, width and spacing, so letter-spaced or wrapped text still matches"""
    return "".join(unicodedata.normalize("NFKC", text).casefold().split())


def _values(node: object, path: str) -> Iterator[tuple[str, Value | RichValue]]:
    """Every Value and RichValue under node, with its path of ids or indexes"""
    if isinstance(node, Value | RichValue):
        yield path, node
    elif isinstance(node, BaseModel):
        for name in type(node).model_fields:
            yield from _values(getattr(node, name), f"{path}/{name}")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from _values(item, f"{path}/{getattr(item, 'id', index)}")


def _verbatim(draft: ResumeImport, lines: Sequence[Line]) -> list[CheckError]:
    """Each value's text appears in the lines it cites"""
    order = {line.id: index for index, line in enumerate(lines)}
    errors: list[CheckError] = []
    for path, value in _values(draft.content, "content"):
        if unknown := [source for source in value.src if source not in order]:
            message = f"cites {', '.join(unknown)}, which are not lines"
        elif not value.src:
            message = "cites no lines"
        elif _normal(value.text) not in _normal(
            "".join(lines[index].text for index in sorted(order[s] for s in value.src))
        ):
            message = f"{value.text!r} is not the text of {', '.join(value.src)}"
        else:
            continue
        errors.append(CheckError(check=Check.VERBATIM, path=path, message=message))
    return errors


def _coverage(draft: ResumeImport, lines: Sequence[Line]) -> list[CheckError]:
    """Each line is cited by a value or skipped, and only lines are skipped"""
    ids = {line.id for line in lines}
    cited = {s for _, value in _values(draft.content, "content") for s in value.src}
    errors: list[CheckError] = []
    if unknown := [source for source in draft.skipped if source not in ids]:
        errors.append(
            CheckError(
                check=Check.COVERAGE,
                path="skipped",
                message=f"{', '.join(unknown)} are not lines",
            )
        )
    if missing := [
        line for line in lines if line.id not in cited and line.id not in draft.skipped
    ]:
        errors.append(
            CheckError(
                check=Check.COVERAGE,
                path="content",
                message="these lines are neither cited nor skipped: "
                + "; ".join(f"{line.id} {line.text!r}" for line in missing),
            )
        )
    return errors


def _order(draft: ResumeImport, lines: Sequence[Line]) -> list[CheckError]:
    """Each block starts after the block before it"""
    order = {line.id: index for index, line in enumerate(lines)}
    starts = [
        (block.id, min(found))
        for block in draft.content.blocks
        if (
            found := [
                order[source]
                for _, value in _values(block, "")
                for source in value.src
                if source in order
            ]
        )
    ]
    return [
        CheckError(
            check=Check.ORDER,
            path=f"content/blocks/{block}",
            message=f"starts at {lines[start].id}, before {previous} at"
            f" {lines[previous_start].id}, so it must come first",
        )
        for (previous, previous_start), (block, start) in pairwise(starts)
        if start < previous_start
    ]


CHECKS: dict[Check, Callable[[ResumeImport, Sequence[Line]], list[CheckError]]] = {
    Check.SCHEMA: lambda draft, lines: [],
    Check.VERBATIM: _verbatim,
    Check.COVERAGE: _coverage,
    Check.ORDER: _order,
}
"""What each check finds; the schema check runs before them all"""


def validate_resume(
    reply: object, lines: Sequence[Line], checks: Collection[Check] = tuple(Check)
) -> list[CheckError]:
    """Checks a ResumeImport against the lines it came from; empty when it passes"""
    try:
        draft = ResumeImport.model_validate(reply)
    except ValidationError as error:
        return [
            CheckError(
                check=Check.SCHEMA,
                path="/".join(str(part) for part in issue["loc"]),
                message=issue["msg"],
            )
            for issue in error.errors()
        ]
    return [error for check in checks for error in CHECKS[check](draft, lines)]
