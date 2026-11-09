from __future__ import annotations

from typing import Annotated, Literal

from pydantic import StringConstraints

YearMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
"""A month as YYYY-MM"""

EntryEnd = YearMonth | Literal["present"]
"""The last month of an entry, or present while it is ongoing"""

CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
"""ISO 3166-1 alpha-2 country code, such as GB"""

CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
"""ISO 4217 currency code, such as MYR"""

FactId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
"""Key the agents cite as fact:<id>"""

Highlight = Annotated[str, StringConstraints(min_length=1)]
"""One achievement sentence"""

Link = Annotated[str, StringConstraints(min_length=1)]
"""A profile or portfolio URL"""


__all__ = [
    "CountryCode",
    "CurrencyCode",
    "EntryEnd",
    "FactId",
    "Highlight",
    "Link",
    "YearMonth",
]
