import json
from typing import NotRequired, TypedDict

from langchain_core.messages import HumanMessage
from openinference.instrumentation.langchain import get_current_span

from src.shared.checks.check_error import CheckError


class CheckRound(TypedDict):
    errors: list[CheckError]
    """What the check found; empty when the answer passed"""

    messages: NotRequired[list[HumanMessage]]
    """A message asking the agent to fix the errors, when there are any"""


def check_round(errors: list[CheckError]) -> CheckRound:
    """Record a check round on the running node's span and return the state
    update: the errors, plus a message asking the agent to fix any"""
    if span := get_current_span():
        span.set_attribute("check.error_count", len(errors))
        span.set_attribute(
            "check.errors", json.dumps([error.model_dump() for error in errors])
        )
    if not errors:
        return {"errors": []}
    found = "\n".join(f"- {e.at} ({e.rule}): {e.message}" for e in errors)
    return {
        "errors": errors,
        "messages": [HumanMessage(f"The check found errors. Fix them:\n{found}")],
    }
