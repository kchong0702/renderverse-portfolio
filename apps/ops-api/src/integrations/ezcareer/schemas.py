from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ModelFamily = Literal["claude", "glm", "openai"]
"""A model provider ezcareer-harness can run"""


class FamilyModels(BaseModel):
    family: ModelFamily
    """The provider"""

    models: list[str]
    """Model names ezcareer-harness offers for it"""


class ModelCatalog(BaseModel):
    families: list[FamilyModels]
    """Every provider ezcareer-harness offers, with its models"""


__all__ = ["FamilyModels", "ModelCatalog", "ModelFamily"]
