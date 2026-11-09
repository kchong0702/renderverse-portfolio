from typing import Literal

from pydantic import BaseModel, ConfigDict


class ImportResumeConfigurations(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    family: Literal["claude", "glm", "openai"]
    """Model family, which picks the provider"""

    model: str
    """Exact model that reads the résumé, such as gpt-6-luna"""
