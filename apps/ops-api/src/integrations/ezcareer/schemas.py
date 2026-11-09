from __future__ import annotations

from pydantic import BaseModel

from src.integrations.ezcareer.types import ModelFamily


class FamilyModels(BaseModel):
    family: ModelFamily
    """The provider"""

    models: list[str]
    """Model names ezcareer-harness offers for it"""


class ModelCatalog(BaseModel):
    families: list[FamilyModels]
    """Every provider ezcareer-harness offers, with its models"""


__all__ = ["FamilyModels", "ModelCatalog"]
