from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

from src.core.providers import Provider


class GoogleDetails(BaseModel):
    provider: Literal[Provider.GOOGLE] = Provider.GOOGLE
    """Marks these as Google's details"""

    scopes: list[str] = Field(default_factory=list)
    """Scopes the grant allows"""


class JSearchDetails(BaseModel):
    provider: Literal[Provider.JSEARCH] = Provider.JSEARCH
    """Marks these as JSearch's details"""

    quota_remaining: int | None = None
    """Calls left on the key, as the last run read them; None when not known"""

    quota_limit: int | None = None
    """Calls the key allows each period; None when not known"""


ConnectionDetails = Annotated[
    GoogleDetails | JSearchDetails, Field(discriminator="provider")
]
"""What one provider's connection keeps beyond the shared columns"""

__all__ = ["ConnectionDetails", "GoogleDetails", "JSearchDetails"]
