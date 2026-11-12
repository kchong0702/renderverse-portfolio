from functools import partial, update_wrapper

from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.types import interrupt
from pydantic import ConfigDict, Field, TypeAdapter, ValidationError, create_model

from src.agents.productivity_assistant.types import FetchedThread
from src.core.errors import ExecuteError
from src.shared.email import latest_messages, untrusted_thread
from src.shared.fetch_failed import FetchFailed
from src.shared.tool_artifact import StepDetail


def _read_thread(
    max_messages: int, max_chars: int, thread_id: str
) -> tuple[str, StepDetail]:
    """Reads one email thread's latest messages, each with its sender and time"""
    try:
        fetched = TypeAdapter(FetchedThread | FetchFailed).validate_python(
            interrupt({"fetch": "thread", "id": thread_id})
        )
    except ValidationError as error:
        raise ExecuteError(f"The thread didn't load: {error}") from error
    if isinstance(fetched, FetchFailed):
        raise ToolException(fetched.error)
    thread = latest_messages(fetched.thread, max_messages, max_chars)
    left_out = len(fetched.thread.messages) - len(thread.messages)
    earlier = f"{left_out} earlier messages are left out.\n\n" if left_out else ""
    return f"{earlier}{untrusted_thread(thread)}", {
        "step_detail": f"{len(fetched.thread.messages)} messages"
        if len(fetched.thread.messages) > 1
        else "1 message"
    }


def read_thread_tool(max_messages: int, max_chars: int) -> BaseTool:
    """read_thread, which shows the agent a thread's latest max_messages messages,
    each cut to max_chars"""
    return StructuredTool.from_function(
        func=update_wrapper(
            partial(_read_thread, max_messages, max_chars), _read_thread
        ),
        name="read_thread",
        args_schema=create_model(
            "ReadThreadArgs",
            __config__=ConfigDict(extra="forbid"),
            thread_id=(str, Field(description="The email thread's id")),
        ),
        response_format="content_and_artifact",
        handle_tool_error=True,
    )
