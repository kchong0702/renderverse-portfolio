from __future__ import annotations

import re
from typing import Literal

from rapidfuzz import fuzz, utils

from src.features.profile.models import ProfileEntry
from src.features.profile.schemas import ImportedEntry
from src.features.profile.types import ChangeField, FieldValue

ABOUT_FIELDS: tuple[ChangeField, ...] = (
    "name",
    "headline",
    "location",
    "email",
    "phone",
    "summary",
)

ENTRY_FIELDS: tuple[ChangeField, ...] = (
    "title",
    "organisation",
    "location",
    "start",
    "end",
    "summary",
    "highlights",
    "link",
    "code_link",
    "tools",
)


def normalised(text: str) -> str:
    """Casefolded words without punctuation"""
    return " ".join(re.sub(r"[^\w\s]", " ", text.casefold()).split())


def agrees(field: ChangeField, current: FieldValue, incoming: FieldValue) -> bool:
    """Whether an imported value says what the current one does; a year-only start
    or end agrees with any month of that year"""
    if field in ("start", "end"):
        return isinstance(current, str) and current.startswith(str(incoming))
    if isinstance(incoming, list):
        return [normalised(v) for v in current or []] == [
            normalised(v) for v in incoming
        ]
    return normalised(str(current or "")) == normalised(str(incoming or ""))


def stored(field: ChangeField, value: FieldValue) -> FieldValue:
    """An imported value as the profile keeps it: a year-only start becomes its
    January and a year-only end its December"""
    if isinstance(value, str) and len(value) == 4 and field in ("start", "end"):
        return f"{value}-01" if field == "start" else f"{value}-12"
    return value


def entry_match(
    entry: ProfileEntry, incoming: ImportedEntry, cutoff: int
) -> Literal["exact", "unsure"] | None:
    """exact when the kind, start, organisation and title agree; unsure when the
    organisation or title only come close; None otherwise"""
    starts = (entry.start or "", incoming.start or "")
    if entry.kind is not incoming.kind or not (
        starts[0].startswith(starts[1]) or starts[1].startswith(starts[0])
    ):
        return None
    pairs = (
        (entry.organisation, incoming.organisation),
        (entry.title, incoming.title),
    )
    if all(normalised(a) == normalised(b) for a, b in pairs):
        return "exact"
    if all(
        normalised(a) == normalised(b)
        or fuzz.token_set_ratio(a, b, processor=utils.default_process) >= cutoff
        for a, b in pairs
    ):
        return "unsure"
    return None


__all__ = [
    "ABOUT_FIELDS",
    "ENTRY_FIELDS",
    "agrees",
    "entry_match",
    "normalised",
    "stored",
]
