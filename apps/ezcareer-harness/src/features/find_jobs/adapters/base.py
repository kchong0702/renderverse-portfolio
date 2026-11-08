from pydantic import BaseModel, ConfigDict, Field, JsonValue

from src.features.find_jobs.schemas import JobPosting


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    postings: list[JobPosting]
    """The jobs found, in the source's order"""

    notes: dict[str, JsonValue] = Field(default_factory=dict)
    """What the agent should know about the source, such as its requests left"""
