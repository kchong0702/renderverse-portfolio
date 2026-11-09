from typing import NotRequired

from document_schema import AnyDocument, Report

from src.agents.state import ProfileState
from src.shared.extraction.types import Line
from src.shared.profile import Preferences


class CareerDirectorState(ProfileState):
    preferences: Preferences
    """What the user wants from a job"""

    document: NotRequired[AnyDocument]
    """The résumé or letter open in the app, if any"""

    report: NotRequired[Report | None]
    """How that document last printed; None before its first render"""

    lines: NotRequired[list[Line]]
    """That document's uploaded PDF lines, which it cites as p<page>.s<n>"""
