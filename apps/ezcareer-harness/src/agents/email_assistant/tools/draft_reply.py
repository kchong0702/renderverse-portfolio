from collections.abc import Callable
from functools import partial, update_wrapper

from langchain.tools import ToolRuntime
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from pydantic import ConfigDict, Field, TypeAdapter, ValidationError, create_model
from pydantic_core import to_json

from src.agents.email_assistant.types import FetchedThread, FreeSlots
from src.agents.state import ProfileState
from src.core.errors import ExecuteError
from src.shared.fetch_failed import FetchFailed


async def _draft_reply(
    graph: Callable[[], CompiledStateGraph],
    runtime: ToolRuntime[None, ProfileState],
    thread_id: str,
    request: str | None = None,
    days: int = 7,
) -> str:
    """Drafts the user's reply to one email thread, offering free times when the
    email asks for them; it never sends anything"""
    try:
        fetched = TypeAdapter(FetchedThread | FetchFailed).validate_python(
            interrupt({"fetch": "thread", "id": thread_id})
        )
    except ValidationError as error:
        raise ExecuteError(f"The thread didn't load: {error}") from error
    if isinstance(fetched, FetchFailed):
        raise ToolException(fetched.error)
    try:
        free = FreeSlots.model_validate(
            interrupt({"fetch": "free_slots", "days": days})
        )
    except ValidationError as error:
        raise ExecuteError(f"The free slots didn't load: {error}") from error
    workflow = graph()
    try:
        output = await workflow.ainvoke(
            workflow.get_input_schema().model_validate(
                {
                    "thread": fetched.thread,
                    "free_slots": free.free_slots,
                    "timezone": free.timezone,
                    "facts": runtime.state["facts"],
                    "messages": [HumanMessage(request)] if request else [],
                }
            )
        )
    except (ValidationError, ExecuteError) as error:
        raise ToolException(str(error)) from error
    return to_json(output).decode()


def draft_reply_tool(graph: Callable[[], CompiledStateGraph]) -> BaseTool:
    """draft_reply over the draft-reply workflow that graph returns when called, so
    the workflow can run the agent that owns this tool"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(partial(_draft_reply, graph), _draft_reply),
        name="draft_reply",
        args_schema=create_model(
            "DraftReplyArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            runtime=(
                ToolRuntime[None, ProfileState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
            thread_id=(str, Field(description="The email thread's id")),
            request=(
                str | None,
                Field(
                    default=None,
                    description="What the user wants the reply to say, in their own words, if they said",
                ),
            ),
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
        handle_tool_error=True,
    )
