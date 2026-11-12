from __future__ import annotations

from typing import Annotated

from pydantic import StringConstraints

CountryCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")]
"""ISO 3166-1 alpha-2 country code, such as GB"""

CurrencyCode = Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
"""ISO 4217 currency code, such as MYR"""


__all__ = ["CountryCode", "CurrencyCode"]
