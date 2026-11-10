from pydantic import BaseModel, ConfigDict


class FetchFailed(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    error: str
    """Why the client couldn't send what a data request asked for"""
