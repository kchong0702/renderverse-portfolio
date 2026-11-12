from functools import partial, update_wrapper

from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import interrupt
from pydantic import ConfigDict, Field, ValidationError, create_model

from src.agents.productivity_assistant.types import FreeSlots
from src.core.errors import ExecuteError
from src.shared.tool_artifact import StepDetail


def _read_free_slots(max_slots: int, days: int = 7) -> tuple[str, StepDetail]:
    """Lists the earliest times the user is free, in their time zone"""
    try:
        free = FreeSlots.model_validate(
            interrupt({"fetch": "free_slots", "days": days})
        )
    except ValidationError as error:
        raise ExecuteError(f"The free slots didn't load: {error}") from error
    slots = sorted(free.free_slots, key=lambda slot: slot.start)[:max_slots]
    if not slots:
        return "The user has no free times to offer.", {"step_detail": "no free slots"}
    times = "\n".join(
        f"- {slot.start.astimezone(free.timezone):%a %d %b %H:%M}"
        f" to {slot.end.astimezone(free.timezone):%H:%M}"
        for slot in slots
    )
    return f"The user's free times, in {free.timezone.key}:\n{times}", {
        "step_detail": f"{len(slots)} free slots" if len(slots) > 1 else "1 free slot"
    }


def read_free_slots_tool(max_slots: int) -> BaseTool:
    """read_free_slots, which shows the agent the user's earliest max_slots free
    times"""
    return StructuredTool.from_function(
        func=update_wrapper(partial(_read_free_slots, max_slots), _read_free_slots),
        name="read_free_slots",
        args_schema=create_model(
            "ReadFreeSlotsArgs",
            __config__=ConfigDict(extra="forbid"),
            days=(
                int,
                Field(
                    default=7,
                    ge=1,
                    le=30,
                    description="How many days ahead to look for free times",
                ),
            ),
        ),
        response_format="content_and_artifact",
    )
