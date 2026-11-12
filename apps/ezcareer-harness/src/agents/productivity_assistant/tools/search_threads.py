from datetime import date
from functools import partial, update_wrapper

from langchain_core.tools import BaseTool, StructuredTool, ToolException
from langgraph.types import interrupt
from pydantic import ConfigDict, Field, TypeAdapter, ValidationError, create_model
from pydantic_core import to_json

from src.agents.productivity_assistant.types import FoundThreads
from src.core.errors import ExecuteError
from src.shared.fetch_failed import FetchFailed
from src.shared.tool_artifact import StepDetail


def _search_threads(
    max_threads: int,
    since: date | None = None,
    until: date | None = None,
    keyword: str | None = None,
    sender: str | None = None,
    has_attachment: bool | None = None,
) -> tuple[str, StepDetail]:
    """Finds the user's email threads that match every filter given, latest first,
    each with the id read_thread takes"""
    try:
        found = TypeAdapter(FoundThreads | FetchFailed).validate_python(
            interrupt(
                {
                    "fetch": "threads",
                    "since": since and since.isoformat(),
                    "until": until and until.isoformat(),
                    "keyword": keyword,
                    "sender": sender,
                    "has_attachment": has_attachment,
                    "limit": max_threads,
                }
            )
        )
    except ValidationError as error:
        raise ExecuteError(f"The threads didn't load: {error}") from error
    if isinstance(found, FetchFailed):
        raise ToolException(found.error)
    shown = found.threads[:max_threads]
    hidden = max(found.total, len(found.threads)) - len(shown)
    threads = f"<threads untrusted>\n{to_json(shown).decode()}\n</threads>"
    if not hidden:
        return threads, {
            "step_detail": f"{len(shown)} {'thread' if len(shown) == 1 else 'threads'}"
        }
    return (
        (
            f"{threads}\n\nMatching threads not shown: {hidden}. Tell the user how"
            " many were left out, and ask them to narrow the search with a shorter"
            " date range, a sender, a keyword or attachments."
        ),
        {"step_detail": f"{len(shown)} of {len(shown) + hidden} threads"},
    )


def search_threads_tool(max_threads: int) -> BaseTool:
    """search_threads, which shows the agent at most max_threads threads and says
    how many more match"""
    return StructuredTool.from_function(
        func=update_wrapper(partial(_search_threads, max_threads), _search_threads),
        name="search_threads",
        args_schema=create_model(
            "SearchThreadsArgs",
            __config__=ConfigDict(extra="forbid"),
            since=(
                date | None,
                Field(default=None, description="Earliest day a message was sent"),
            ),
            until=(
                date | None,
                Field(default=None, description="Latest day a message was sent"),
            ),
            keyword=(
                str | None,
                Field(
                    default=None,
                    description="Words the subject or a message contains",
                ),
            ),
            sender=(
                str | None,
                Field(
                    default=None,
                    description="A sender's name, address or domain, such as acme.com",
                ),
            ),
            has_attachment=(
                bool | None,
                Field(
                    default=None,
                    description="True for threads with an attachment, false for those without",
                ),
            ),
        ),
        response_format="content_and_artifact",
        handle_tool_error=True,
    )
