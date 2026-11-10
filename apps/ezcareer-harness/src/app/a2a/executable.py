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
from a2a.types import Message, TaskState
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, TaskPayload, TaskResultPayload
from pydantic import BaseModel, ConfigDict, Field, RootModel, ValidationError
from pydantic_core import to_jsonable_python

from src.clients.llm_providers import llm_provider
from src.core.config import Family, get_settings
from src.core.errors import ExecuteError
from src.shared.run_context import RunContext


def _reason(updater: TaskUpdater, text: str) -> Message:
    """An agent message carrying the reason a run stopped"""
    return updater.new_agent_message([new_text_part(text)])


class ModelChoice(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    family: Family
    """The model's family"""

    model: str
    """A model [models] offers for that family"""


class RunMetadata(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    model: ModelChoice
    """The model the user picked for the run"""


class Step(BaseModel):
    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    id: str
    """The tool call or graph task the step is"""

    parent: str | None
    """The tool call whose workflow runs this step, if any"""

    name: str
    """The tool or graph node, such as analyse_job or fetch"""

    status: Literal["running", "done", "failed", "waiting"]
    """Where the step is"""

    detail: str | None = None
    """What the step found or worked on, in plain words, such as 1 cover letter"""


def _details(task: TaskResultPayload) -> dict[str, str]:
    """The step detail each tool call in the task's result returned, by call id"""
    details: dict[str, str] = {}
    for message in task["result"].get("messages", []):
        match message:
            case ToolMessage(artifact={"step_detail": str() as detail}):
                details[message.tool_call_id] = detail
    return details


def _steps(
    kind: Literal["workflow", "agent"],
    namespace: tuple[str, ...],
    task: TaskPayload | TaskResultPayload,
    calls: dict[str, list[tuple[str, str]]],
) -> list[Step]:
    """The steps a graph task starts or ends: an agent's tool calls and the nodes of
    the workflows they run, or a workflow's own nodes, with the details tools set"""
    if "." in task["name"]:
        return []
    status: Literal["running", "done", "failed", "waiting"]
    if "input" in task:
        status = "running"
    elif task["error"] or any(
        isinstance(m, ToolMessage) and m.status == "error"
        for m in task["result"].get("messages", [])
    ):
        status = "failed"
    else:
        status = "waiting" if task["interrupts"] else "done"
    details = {} if "input" in task else _details(task)
    detail = [*details.values()][-1] if details else None
    if kind == "workflow":
        return (
            []
            if namespace
            else [
                Step(
                    id=task["id"],
                    parent=None,
                    name=task["name"],
                    status=status,
                    detail=detail,
                )
            ]
        )
    if not namespace and task["name"] == "tools":
        if "input" in task:
            calls[task["id"]] = [(call["id"], call["name"]) for call in task["input"]]
        return [
            Step(
                id=call_id,
                parent=None,
                name=name,
                status=status,
                detail=details.get(call_id),
            )
            for call_id, name in calls.get(task["id"], [])
        ]
    if len(namespace) == 1 and (
        parent := calls.get(namespace[0].removeprefix("tools:"))
    ):
        return [
            Step(
                id=task["id"],
                parent=parent[0][0],
                name=task["name"],
                status=status,
                detail=detail,
            )
        ]
    return []


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

    reply_node: str | None = None
    """The workflow node whose model streams its thinking and text to the user;
    None streams an agent's own model and nothing of a workflow's"""


class LanggraphExecutor(AgentExecutor):
    def __init__(self, executable: Executable) -> None:
        """Runs the executable's graph as one A2A task per run"""
        self.executable = executable

    @override
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Run or resume the graph, on the model the request metadata names, and
        report it as completed, failed or input required"""
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        data = get_data_parts(context.message.parts) if context.message else []
        if context.current_task is None and context.message:
            await event_queue.enqueue_event(new_task_from_user_message(context.message))
        await updater.start_work()
        try:
            metadata = (
                RunMetadata.model_validate(context.metadata)
                if context.metadata
                else None
            )
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
        if metadata and not get_settings().offers(
            metadata.model.family, metadata.model.model
        ):
            await updater.failed(
                _reason(
                    updater,
                    f"ezcareer-harness does not offer {metadata.model.model} for {metadata.model.family}",
                )
            )
            return
        result = {}
        opened: set[str] = set()
        calls: dict[str, list[tuple[str, str]]] = {}
        try:
            async for namespace, mode, data in self.executable.graph.astream(
                graph_input,
                {
                    "configurable": {
                        "thread_id": context.context_id
                        if self.executable.kind == "agent"
                        else context.task_id
                    }
                },
                context=RunContext(
                    model=llm_provider(metadata.model.family, metadata.model.model)
                )
                if metadata
                else None,
                stream_mode=["values", "messages", "tasks"],
                output_keys=self.executable.graph.output_channels,
                subgraphs=True,
            ):
                if mode == "values" and not namespace:
                    result = data
                elif mode == "messages" and tuple(
                    segment.partition(":")[0] for segment in namespace
                ) == (
                    (self.executable.reply_node,) if self.executable.reply_node else ()
                ):
                    chunk, meta = data
                    if not (
                        isinstance(chunk, AIMessage)
                        and meta["langgraph_node"] == "model"
                    ):
                        continue
                    for block in chunk.content_blocks:
                        if block["type"] == "reasoning":
                            name, text = "thinking", block.get("reasoning")
                        elif block["type"] == "text":
                            name, text = "text", block["text"]
                        else:
                            continue
                        if not text:
                            continue
                        artifact_id = f"{name}-{meta['langgraph_checkpoint_ns']}"
                        await updater.add_artifact(
                            [new_text_part(text)],
                            artifact_id=artifact_id,
                            name=name,
                            append=artifact_id in opened,
                        )
                        opened.add(artifact_id)
                elif mode == "tasks":
                    for step in _steps(self.executable.kind, namespace, data, calls):
                        await updater.update_status(
                            TaskState.TASK_STATE_WORKING,
                            updater.new_agent_message(
                                [new_data_part({"step": step.model_dump()})]
                            ),
                        )
                    if namespace or data["name"] != "tools" or "result" not in data:
                        continue
                    for message in data["result"].get("messages", []):
                        match message:
                            case ToolMessage(
                                artifact={"name": str() as name, "data": artifact}
                            ):
                                await updater.add_artifact(
                                    [new_data_part(to_jsonable_python(artifact))],
                                    name=name,
                                    append=False,
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
