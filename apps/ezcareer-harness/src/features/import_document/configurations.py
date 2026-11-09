from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ImportResumeConfigurations(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    family: Literal["claude", "glm", "openai"]
    """Model family, which picks the provider"""

    model: str
    """Exact model that reads the résumé, such as gpt-6-luna"""

    checks: list[Literal["verbatim", "coverage", "order"]]
    """Checks run on each reply; errors go back to the LLM"""

    recursion_limit: int = Field(gt=0)
    """Graph steps a run may take across all check rounds"""

    max_skipped_length: int = Field(ge=0)
    """Most letters and digits a skipped line may hold, unless the file repeats it"""

    max_joining_word_length: int = Field(ge=0)
    """Longest word a value may leave out of the lines it cites, such as at"""
