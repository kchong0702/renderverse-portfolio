from collections.abc import Callable, Sequence
from typing import Any
from zoneinfo import ZoneInfo

from a2a.helpers import get_data_parts
from a2a.server.agent_execution import RequestContext
from google.protobuf.json_format import MessageToDict
from langchain_core.messages import HumanMessage
from langgraph.types import Command, Interrupt, StateSnapshot
from pydantic import AwareDatetime, BaseModel, ConfigDict, RootModel, ValidationError

from src.app.a2a.executable import Executable
from src.core.errors import ExecuteError


class MessageMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    created_at: AwareDatetime
    """When the user sent the message"""

    timezone: ZoneInfo | None = None
    """The user's time zone when they sent it, such as Europe/London; None is UTC"""


def questions_first(interrupts: Sequence[Interrupt]) -> list[Interrupt]:
    """The interrupts with the user's questions before the data requests, so the
    first is the one a bare answer goes to"""
    return sorted(
        interrupts,
        key=lambda pending: (
            isinstance(pending.value, dict) and "execute_tool" in pending.value
        ),
    )


class Start:
    resumes = False
    """A new message starts a run of its own"""

    async def graph_input(
        self,
        executable: Executable,
        context: RequestContext,
        snapshot: StateSnapshot | None,
    ) -> Any:
        """The new message as the graph's input, an agent's stamped with when the
        user sent it, and with the data part's fields"""
        text = context.get_user_input()
        message = context.message
        try:
            if text and message and executable.kind == "agent":
                sent = MessageMetadata.model_validate(MessageToDict(message.metadata))
                zone = sent.timezone or ZoneInfo("UTC")
                stamp = f"{sent.created_at.astimezone(zone):%a %d %b %Y, %H:%M}"
                messages = [
                    HumanMessage(f"[{stamp} {zone.key}] {text}", id=message.message_id)
                ]
            else:
                messages = [HumanMessage(text)] if text else []
            data = get_data_parts(message.parts if message else [])
            graph_input = executable.graph.get_input_schema().model_validate(
                {**(data[0] if data else {}), "messages": messages}
            )
        except ValidationError as error:
            raise ExecuteError(f"Invalid input: {error}") from error
        return graph_input.root if isinstance(graph_input, RootModel) else graph_input


class Answer:
    resumes = True
    """An answer goes on from the pause it answers"""

    async def graph_input(
        self,
        executable: Executable,
        context: RequestContext,
        snapshot: StateSnapshot,
    ) -> Command:
        """The message's answers as a resume of the task's pause, while the thread's
        latest checkpoint, snapshot, is still the task's own"""
        if (snapshot.metadata or {}).get("task_id") != context.task_id:
            raise ExecuteError("This question was replaced by a newer message")
        parts = context.message.parts if context.message else []
        data = get_data_parts(parts)
        ids = [
            part.metadata["interrupt_id"]
            for part in parts
            if "interrupt_id" in part.metadata
        ]
        if ids:
            return Command(resume=dict(zip(ids, data, strict=True)))
        if paused := next(iter(questions_first(snapshot.interrupts)), None):
            return Command(
                resume={paused.id: data[0] if data else context.get_user_input()}
            )
        raise ExecuteError("There is no question waiting for an answer")


class Restart:
    resumes = True
    """A takeover goes on from where the dead process stopped"""

    async def graph_input(
        self,
        executable: Executable,
        context: RequestContext,
        snapshot: StateSnapshot,
    ) -> None:
        """No input, so a taken-over task resumes from the thread's latest checkpoint,
        snapshot, when it is the task's own and the takeover allows it"""
        if (snapshot.metadata or {}).get("task_id") != context.task_id or (
            context.message.metadata["restart"] == "fail"
        ):
            raise ExecuteError("The assistant restarted")


GRAPH_INPUTS: tuple[
    tuple[Callable[[RequestContext], bool], Start | Answer | Restart], ...
] = (
    (
        lambda context: bool(
            context.message and MessageToDict(context.message.metadata).get("restart")
        ),
        Restart(),
    ),
    (lambda context: context.current_task is not None, Answer()),
    (lambda context: True, Start()),
)
"""How each request becomes the graph's input, checked in order, with when it
applies: a takeover's restart, an answer to the task's pause, or a new message"""
