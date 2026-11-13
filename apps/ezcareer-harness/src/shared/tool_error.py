from pydantic import BaseModel, ConfigDict


class ToolError(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    error: str
    """Why ops-api couldn't execute the tool"""
