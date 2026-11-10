from typing import TypedDict

from pydantic import JsonValue


class ToolArtifact(TypedDict):
    name: str
    """The A2A artifact's name, such as changeset"""

    data: JsonValue
    """The artifact's one data part"""
