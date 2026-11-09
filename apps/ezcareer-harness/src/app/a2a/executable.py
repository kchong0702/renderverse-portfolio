from typing import Literal, override

from a2a.helpers import (
    get_data_parts,
    new_data_part,
    new_task_from_user_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import BaseModel, ConfigDict, Field, RootModel, ValidationError
from pydantic_core import to_jsonable_python

from src.core.errors import ExecuteError


def _reason(updater: TaskUpdater, text: str) -> Message:
    """An agent message carrying the reason a run stopped"""
    return updater.new_agent_message([new_text_part(text)])


class Executable(BaseModel):
    model_config = ConfigDict(
        frozen=True, arbitrary_types_allowed=True, use_attribute_docstrings=True
    )

    name: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    """Path segment and agent card name, such as analyse-job"""

    description: str
    """What the graph does, shown on its agent card"""

    kind: Literal["workflow", "agent"] = "workflow"
    """A workflow runs one task end to end; an agent is a shared agent the user
    talks to; both take the user's text as their message"""

    graph: CompiledStateGraph
    """The graph it runs; with a checkpointer it can pause for input and resume"""


class LanggraphExecutor(AgentExecutor):
    def __init__(self, executable: Executable) -> None:
        """Runs the executable's graph as one A2A task per run"""
        self.executable = executable

    @override
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Run or resume the graph and report it as completed, failed or
        input required"""
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        data = get_data_parts(context.message.parts) if context.message else []
        if context.current_task is None and context.message:
            await event_queue.enqueue_event(new_task_from_user_message(context.message))
        await updater.start_work()
        try:
            if context.current_task:
                graph_input = Command(
                    resume=data[0] if data else context.get_user_input()
                )
            else:
                graph_input = self.executable.graph.get_input_schema().model_validate(
                    {
                        **(data[0] if data else {}),
                        "messages": [HumanMessage(text)]
                        if (text := context.get_user_input())
                        else [],
                    }
                )
                if isinstance(graph_input, RootModel):
                    graph_input = graph_input.root
        except ValidationError as error:
            await updater.failed(_reason(updater, f"Invalid input: {error}"))
            return
        try:
            result = await self.executable.graph.ainvoke(
                graph_input, {"configurable": {"thread_id": context.task_id}}
            )
        except GraphRecursionError:
            await updater.failed(_reason(updater, "Ran out of steps before finishing"))
            return
        except ExecuteError as error:
            await updater.failed(_reason(updater, str(error)))
            return
        if interrupts := result.pop("__interrupt__", None):
            await updater.requires_input(
                updater.new_agent_message(
                    [new_data_part(to_jsonable_python(i.value)) for i in interrupts]
                )
            )
            return
        if self.executable.kind == "workflow":
            reply = new_data_part(to_jsonable_python(result))
        elif structured := result.get("structured_response"):
            reply = new_data_part(to_jsonable_python(structured))
        else:
            reply = new_text_part(result["messages"][-1].text)
        await updater.add_artifact([reply], name=self.executable.name)
        await updater.complete()

    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Mark the task cancelled once the SDK has stopped the run"""
        await TaskUpdater(event_queue, context.task_id, context.context_id).cancel()
