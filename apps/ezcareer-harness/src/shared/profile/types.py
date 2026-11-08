from typing import Annotated

from pydantic import StringConstraints

FactRef = Annotated[str, StringConstraints(pattern=r"^fact:[A-Za-z0-9_-]{1,64}$")]
"""A profile fact cited as fact:<id>"""

CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
"""ISO 3166-1 alpha-2 country code, such as GB"""

YearMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}$")]
"""A month as YYYY-MM"""
