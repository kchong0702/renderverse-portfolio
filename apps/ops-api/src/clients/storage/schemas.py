from pydantic import BaseModel


class UploadTarget(BaseModel):
    url: str
    """Where the browser PUTs the file"""

    headers: dict[str, str]
    """Headers the PUT must send unchanged"""


__all__ = ["UploadTarget"]
