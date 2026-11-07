import unicodedata
from collections import Counter
from collections.abc import Callable, Collection, Iterator, Sequence
from enum import StrEnum
from itertools import pairwise

from document_schema import RichValue, Value
from pydantic import BaseModel, ValidationError

from src.shared.checks.check_error import CheckError
from src.shared.extraction import Line
from src.shared.models.resume_import import ResumeImport


class Check(StrEnum):
    SCHEMA = "schema"
    """The reply is a valid ResumeImport; always runs"""

    VERBATIM = "verbatim"
    """Each value's text appears in the lines it cites"""

    COVERAGE = "coverage"
    """Each line is cited or skipped"""

    ORDER = "order"
    """Blocks follow the order of their lines"""


def _normal(text: str) -> str:
    """Keeps only letters and digits, case folded, so spacing, dashes, quotes and
    hyphenated line breaks don't count"""
    return "".join(
        ch for ch in unicodedata.normalize("NFKC", text).casefold() if ch.isalnum()
    )


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
    """Each value has text, and its text appears in the lines it cites"""
    order = {line.id: index for index, line in enumerate(lines)}
    errors: list[CheckError] = []
    for path, value in _values(draft.blocks, "blocks"):
        if unknown := [source for source in value.src if source not in order]:
            message = f"cites {', '.join(unknown)}, which are not lines"
        elif not value.src:
            message = "cites no lines"
        elif not _normal(value.text):
            message = "has no text"
        elif _normal(value.text) not in _normal(
            "".join(lines[index].text for index in sorted(order[s] for s in value.src))
        ):
            message = f"{value.text!r} is not the text of {', '.join(value.src)}"
        else:
            continue
        errors.append(CheckError(rule=Check.VERBATIM, at=path, message=message))
    return errors


def _coverage(draft: ResumeImport, lines: Sequence[Line]) -> list[CheckError]:
    """Each line is cited with all its words, except joining words of up to three
    letters such as at, or skipped for being short or repeated"""
    order = {line.id: index for index, line in enumerate(lines)}
    texts = [_normal(line.text) for line in lines]
    used = [[False] * len(text) for text in texts]
    for _, value in _values(draft.blocks, "blocks"):
        cited = sorted({order[source] for source in value.src if source in order})
        joined = "".join(texts[index] for index in cited)
        if (start := joined.find(_normal(value.text))) < 0 or not _normal(value.text):
            continue
        end, offset = start + len(_normal(value.text)), 0
        for index in cited:
            for position in range(
                max(start, offset), min(end, offset + len(texts[index]))
            ):
                used[index][position - offset] = True
            offset += len(texts[index])
    cited = {
        source for _, value in _values(draft.blocks, "blocks") for source in value.src
    }
    repeats = Counter(texts)
    errors: list[CheckError] = []
    if unknown := [source for source in draft.skipped if source not in order]:
        errors.append(
            CheckError(
                rule=Check.COVERAGE,
                at="skipped",
                message=f"{', '.join(unknown)} are not lines",
            )
        )
    if content := [
        lines[order[source]]
        for source in draft.skipped
        if source in order
        and len(texts[order[source]]) > 12
        and repeats[texts[order[source]]] == 1
    ]:
        errors.append(
            CheckError(
                rule=Check.COVERAGE,
                at="skipped",
                message="these lines hold content, so cite them instead of skipping"
                " them: " + "; ".join(f"{line.id} {line.text!r}" for line in content),
            )
        )
    dropped: list[str] = []
    for index, line in enumerate(lines):
        if line.id in draft.skipped:
            continue
        left = "".join(
            " " if done else ch for ch, done in zip(texts[index], used[index])
        )
        if line.id not in cited:
            dropped.append(f"{line.id} {line.text!r} (not cited)")
        elif missing := [run for run in left.split() if len(run) > 3]:
            dropped.append(f"{line.id} {line.text!r} (unused: {', '.join(missing)})")
    if dropped:
        errors.append(
            CheckError(
                rule=Check.COVERAGE,
                at="blocks",
                message="cite or skip each of these lines, and use all of a cited"
                " line's words: " + "; ".join(dropped),
            )
        )
    return errors


def _order(draft: ResumeImport, lines: Sequence[Line]) -> list[CheckError]:
    """Each block starts after the block before it"""
    order = {line.id: index for index, line in enumerate(lines)}
    starts = [
        (block.id, min(found))
        for block in draft.blocks
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
            rule=Check.ORDER,
            at=f"blocks/{block}",
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


def schema_errors(error: ValidationError) -> list[CheckError]:
    """A validation error as schema CheckErrors, one per problem"""
    return [
        CheckError(
            rule=Check.SCHEMA,
            at="/".join(str(part) for part in issue["loc"]),
            message=issue["msg"],
        )
        for issue in error.errors()
    ]


def validate_resume(
    reply: object, lines: Sequence[Line], checks: Collection[Check] = tuple(Check)
) -> list[CheckError]:
    """Checks a ResumeImport against the lines it came from; empty when it passes"""
    try:
        draft = ResumeImport.model_validate(reply)
    except ValidationError as error:
        return schema_errors(error)
    return [error for check in checks for error in CHECKS[check](draft, lines)]
