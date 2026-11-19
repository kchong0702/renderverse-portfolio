from datetime import datetime, timedelta

from langchain_core.tools import StructuredTool, ToolException
from langgraph.types import interrupt
from pydantic import ConfigDict, Field, TypeAdapter, ValidationError, create_model
from pydantic_core import to_json

from src.agents.productivity_assistant.types import CalendarEvent, Events
from src.core.errors import ExecuteError
from src.shared.tool_artifact import StepDetail
from src.shared.tool_error import ToolError


def _when(event: CalendarEvent, events: Events) -> str:
    """The event's day and time in the user's time zone"""
    if not isinstance(event.start, datetime) or not isinstance(event.end, datetime):
        last = event.end - timedelta(days=1)
        return (
            f"{event.start:%a %d %b}"
            + (f" to {last:%a %d %b}" if last > event.start else "")
            + ", all day"
        )
    start = event.start.astimezone(events.timezone)
    return f"{start:%a %d %b %H:%M} to {event.end.astimezone(events.timezone):%H:%M}"


def _find_events(days: int = 7) -> tuple[str, StepDetail]:
    """Lists the events on the user's calendar from the start of today, each with its
    time in their time zone"""
    try:
        found = TypeAdapter(Events | ToolError).validate_python(
            interrupt({"execute_tool": "events", "days": days})
        )
    except ValidationError as error:
        raise ExecuteError(f"The calendar didn't load: {error}") from error
    if isinstance(found, ToolError):
        raise ToolException(found.error)
    today = f"Today is {found.today:%a %d %b %Y}, in {found.timezone.key}."
    if not found.events:
        return f"{today} The user has no events in the next {days} days.", {
            "step_detail": "no events"
        }
    shown = [
        {
            "when": _when(event, found),
            "title": event.title,
            "location": event.location,
            "interview": event.interview,
        }
        for event in found.events
    ]
    count = len(found.events)
    return (
        f"{today} The user's events in the next {days} days:\n"
        f"<events untrusted>\n{to_json(shown).decode()}\n</events>"
    ), {"step_detail": f"{count} events" if count != 1 else "1 event"}


find_events = StructuredTool.from_function(
    func=_find_events,
    name="find_events",
    args_schema=create_model(
        "FindEventsArgs",
        __config__=ConfigDict(extra="forbid"),
        days=(
            int,
            Field(
                default=7,
                ge=1,
                le=31,
                description="How many days from the start of today to look in",
            ),
        ),
    ),
    response_format="content_and_artifact",
    handle_tool_error=True,
)
