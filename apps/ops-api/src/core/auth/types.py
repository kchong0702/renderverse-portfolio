from __future__ import annotations

from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator


def _known_zone(name: str) -> str:
    """The name, when it is an IANA time zone; ValueError otherwise"""
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError(f"{name} is not an IANA time zone") from error
    return name


Timezone = Annotated[str, AfterValidator(_known_zone)]
"""An IANA time zone name, such as Asia/Kuala_Lumpur"""


__all__ = ["Timezone"]
