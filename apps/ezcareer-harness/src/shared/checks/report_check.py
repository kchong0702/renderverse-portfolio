from typing import NotRequired, TypedDict

from langchain_core.messages import HumanMessage
from openinference.instrumentation.langchain import get_current_span
from pydantic_core import to_json

from src.shared.checks.check_error import CheckError


class CheckReport(TypedDict):
    errors: list[CheckError]
    """What the check found; empty when the answer passed"""

    messages: NotRequired[list[HumanMessage]]
    """A message asking the agent to fix the errors, when there are any"""


def report_check(errors: list[CheckError]) -> CheckReport:
    """Records a check's errors on the running node's span and returns them as the
    state update, with a message asking the agent to fix any"""
    if span := get_current_span():
        span.set_attribute("check.error_count", len(errors))
        span.set_attribute("check.errors", to_json(errors).decode())
    if not errors:
        return {"errors": []}
    found = "\n".join(f"- {e.at} ({e.rule}): {e.message}" for e in errors)
    return {
        "errors": errors,
        "messages": [HumanMessage(f"The check found errors. Fix them:\n{found}")],
    }
