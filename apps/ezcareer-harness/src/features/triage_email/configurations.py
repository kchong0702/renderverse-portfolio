from pydantic import BaseModel, ConfigDict, Field


class TriageEmailConfigurations(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    recursion_limit: int = Field(gt=0)
    """Most steps the run, and each agent turn within it, may take"""
