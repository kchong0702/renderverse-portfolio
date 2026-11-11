from typing import NotRequired, TypedDict

from pydantic import JsonValue


class StepDetail(TypedDict):
    step_detail: NotRequired[str]
    """What the tool found or worked on, in plain words, such as 1 cover letter"""


class ToolArtifact(StepDetail):
    name: str
    """The A2A artifact's name, such as changeset"""

    data: JsonValue
    """The artifact's one data part"""
