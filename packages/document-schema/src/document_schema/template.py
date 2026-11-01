from __future__ import annotations

import json
from hashlib import sha256

from document_schema.base import SchemaModel
from document_schema.tokens import Tokens


class Template[T: Tokens](SchemaModel):
    html: str
    """Mustache markup with every bound value wrapped in an element carrying
    `data-field="<DataFieldPath>"`"""

    css: str
    """Stylesheet for the markup, reading tokens through `var()`"""

    tokens: T
    """CSS custom properties the template offers, with their default values"""

    @property
    def hash(self) -> str:
        payload = json.dumps(
            [self.html, self.css, self.tokens.model_dump()], sort_keys=True
        )
        return sha256(payload.encode()).hexdigest()
