from __future__ import annotations

import json
from hashlib import sha256
from typing import Annotated

from pydantic import Field, StringConstraints

from document_schema.base import SchemaModel

TokenName = Annotated[str, StringConstraints(pattern=r"^--[A-Za-z0-9-]+$")]

TokenValue = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9#%.,()'\" +_-]*$")]


class Template(SchemaModel):
    html: str
    """Mustache markup with every bound value wrapped in an element carrying
    `data-field="<DataFieldPath>"`"""

    css: str
    """Stylesheet for the markup, reading tokens through `var()`"""

    tokens: dict[TokenName, TokenValue] = Field(default_factory=dict)
    """CSS custom properties the template offers, with their default values"""

    @property
    def hash(self) -> str:
        payload = json.dumps([self.html, self.css, self.tokens], sort_keys=True)
        return sha256(payload.encode()).hexdigest()
