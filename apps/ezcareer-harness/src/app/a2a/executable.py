from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, Literal, override

from a2a.helpers import (
    get_data_parts,
    new_data_part,
    new_task_from_user_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Message, Part, TaskState
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, Interrupt, TaskPayload, TaskResultPayload
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    ValidationError,
)
from pydantic_core import to_jsonable_python

from src.clients.llm_providers import llm_provider
from src.core.config import Family, get_settings
from src.core.errors import ExecuteError
from src.core.types import NextStep
from src.core.usage import UsageReporter
from src.shared.run_context import RunContext


def _reason(
    updater: TaskUpdater, text: str, next_step: NextStep | None = None
) -> Message:
    """An agent message carrying the reason a run stopped, and what the user must
    do first when there is something"""
    return updater.new_agent_message(
        [
            new_text_part(text),
            *([new_data_part({"next": next_step.model_dump()})] if next_step else []),
        ]
    )


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
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        use_attribute_docstrings=True,
    )

    model: ModelChoice | None = None
    """The model the user picked for the run; None keeps each agent's own"""


StepStatus = Literal["running", "done", "failed", "waiting"]
"""Where a step is"""

STEP_STATUSES: tuple[
    tuple[StepStatus, Callable[[TaskPayload | TaskResultPayload, bool], bool]], ...
] = (
    ("running", lambda task, tool_failed: "input" in task),
    ("failed", lambda task, tool_failed: tool_failed or bool(task["error"])),
    ("waiting", lambda task, tool_failed: bool(task["interrupts"])),
)
"""Each status a graph task gives a step, by whether the step's tool calls failed,
checked in order, with when it matches; a step none matches is done"""


class Step(BaseModel):
    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    id: str
    """The tool call or graph task the step is"""

    parent: str | None
    """The tool call whose workflow runs this step, if any"""

    name: str
    """The tool or graph node, such as analyse_job or fetch"""

    status: StepStatus
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
    handoff_agents: frozenset[str],
) -> list[Step]:
    """The steps a graph task starts or ends: an agent's tool calls and the nodes of
    the workflows they run, or a workflow's own nodes, with the details tools set"""
    if "." in task["name"]:
        return []
    tool_errors = (
        set()
        if "input" in task
        else {
            m.tool_call_id
            for m in task["result"].get("messages", [])
            if isinstance(m, ToolMessage) and m.status == "error"
        }
    )

    def step(id: str, parent: str | None, name: str, detail: str | None) -> Step:
        """The step with the status STEP_STATUSES gives it; the task's own step fails
        on any tool error, a tool call's step on its own"""
        tool_failed = bool(tool_errors) if id == task["id"] else id in tool_errors
        return Step(
            id=id,
            parent=parent,
            name=name,
            status=next(
                (
                    status
                    for status, matches in STEP_STATUSES
                    if matches(task, tool_failed)
                ),
                "done",
            ),
            detail=detail,
        )

    details = {} if "input" in task else _details(task)
    detail = [*details.values()][-1] if details else None
    if kind == "workflow":
        return [] if namespace else [step(task["id"], None, task["name"], detail)]
    if not namespace and task["name"] in handoff_agents and "result" in task:
        return [
            step(call_id, None, name, detail)
            for tools in [*calls]
            for call_id, name in calls.pop(tools)
            if (detail := details.get(call_id))
        ]
    if not namespace and task["name"] == "tools":
        if "input" in task:
            calls[task["id"]] = [(call["id"], call["name"]) for call in task["input"]]
        return [
            step(call_id, None, name, details.get(call_id))
            for call_id, name in (
                calls[task["id"]] if "input" in task else calls.pop(task["id"], [])
            )
        ]
    if len(namespace) == 1 and (
        parent := calls.get(namespace[0].removeprefix("tools:"))
    ):
        return [step(task["id"], parent[0][0], task["name"], detail)]
    return []


def _interrupt_part(interrupt: Interrupt) -> Part:
    """The interrupt's value as a data part, tagged with the id its answer comes back
    under"""
    part = new_data_part(to_jsonable_python(interrupt.value))
    part.metadata.update({"interrupt_id": interrupt.id})
    return part


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

    handoff_agents: frozenset[str] = frozenset()
    """The agents of a handoff graph, each a top-level node streamed as the
    conversation's own; empty for workflows and single agents"""


class EventRelay:
    def __init__(self, updater: TaskUpdater, executable: Executable) -> None:
        """Turns one run's stream of the executable's graph into the task's events"""
        self.updater = updater
        """Writes the task's events"""

        self.executable = executable
        """The executable whose graph streams"""

        self.result: dict = {}
        """The top-level graph's latest values"""

        self.interrupts: list[Interrupt] = []
        """Every pause the run stopped at"""

        self.opened: set[str] = set()
        """The ids of the thinking and text artifacts already streamed"""

        self.calls: dict[str, list[tuple[str, str]]] = {}
        """Each running tools task's calls, as (call id, tool name)"""

    def _without_handoff_agent(self, namespace: tuple[str, ...]) -> tuple[str, ...]:
        """The namespace without its handoff agent's node, so whichever agent runs
        streams as the conversation's own"""
        if namespace and (
            namespace[0].partition(":")[0] in self.executable.handoff_agents
        ):
            return namespace[1:]
        return namespace

    async def _values(self, namespace: tuple[str, ...], data: dict) -> None:
        """Keeps the top-level graph's values and the pauses they carry"""
        if namespace:
            return
        self.interrupts += data.get("__interrupt__", [])
        self.result = data

    async def _messages(
        self, namespace: tuple[str, ...], data: tuple[Any, dict]
    ) -> None:
        """Streams the replying model's thinking and text, one artifact per model
        turn"""
        if tuple(
            segment.partition(":")[0]
            for segment in self._without_handoff_agent(namespace)
        ) != ((self.executable.reply_node,) if self.executable.reply_node else ()):
            return
        chunk, meta = data
        if not (isinstance(chunk, AIMessage) and meta["langgraph_node"] == "model"):
            return
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
            await self.updater.add_artifact(
                [new_text_part(text)],
                artifact_id=artifact_id,
                name=name,
                append=artifact_id in self.opened,
            )
            self.opened.add(artifact_id)

    async def _tasks(
        self, namespace: tuple[str, ...], data: TaskPayload | TaskResultPayload
    ) -> None:
        """Reports the steps a graph task starts or ends, then publishes the
        artifacts a top-level tools task's tools returned"""
        namespace = self._without_handoff_agent(namespace)
        for step in _steps(
            self.executable.kind,
            namespace,
            data,
            self.calls,
            self.executable.handoff_agents,
        ):
            await self.updater.update_status(
                TaskState.TASK_STATE_WORKING,
                self.updater.new_agent_message(
                    [new_data_part({"step": step.model_dump()})]
                ),
            )
        if namespace or data["name"] != "tools" or "result" not in data:
            return
        for message in data["result"].get("messages", []):
            match message:
                case ToolMessage(artifact={"name": str() as name, "data": artifact}):
                    await self.updater.add_artifact(
                        [new_data_part(to_jsonable_python(artifact))],
                        name=name,
                        append=False,
                    )

    HANDLERS: ClassVar[dict[str, Callable[..., Awaitable[None]]]] = {
        "values": _values,
        "messages": _messages,
        "tasks": _tasks,
    }
    """Each stream mode's handler"""

    async def handle(self, namespace: tuple[str, ...], mode: str, data: Any) -> None:
        """Relays one streamed chunk with its stream mode's handler"""
        await self.HANDLERS[mode](self, namespace, data)


class LanggraphExecutor(AgentExecutor):
    def __init__(self, executable: Executable) -> None:
        """Runs the executable's graph as one A2A task per run"""
        self.executable = executable

    @override
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Run or resume the graph, on the model the request metadata names, and
        report it as completed, failed or input required"""
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        parts = context.message.parts if context.message else []
        data = get_data_parts(parts)
        ids = [
            part.metadata["interrupt_id"]
            for part in parts
            if "interrupt_id" in part.metadata
        ]
        if context.current_task is None and context.message:
            await event_queue.enqueue_event(new_task_from_user_message(context.message))
        await updater.start_work()
        try:
            metadata = (
                RunMetadata.model_validate(context.metadata)
                if context.metadata
                else None
            )
            if context.current_task and ids:
                graph_input = Command(resume=dict(zip(ids, data, strict=True)))
            elif context.current_task:
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
        if (
            metadata
            and metadata.model
            and not get_settings().offers(metadata.model.family, metadata.model.model)
        ):
            await updater.failed(
                _reason(
                    updater,
                    f"ezcareer-harness does not offer {metadata.model.model} for {metadata.model.family}",
                )
            )
            return
        relay = EventRelay(updater, self.executable)
        try:
            async for namespace, mode, data in self.executable.graph.astream(
                graph_input,
                {
                    "configurable": {
                        "thread_id": context.context_id
                        if self.executable.kind == "agent"
                        else context.task_id
                    },
                    "callbacks": [
                        UsageReporter(
                            lambda usage: updater.update_status(
                                TaskState.TASK_STATE_WORKING,
                                updater.new_agent_message(
                                    [new_data_part({"usage": usage.model_dump()})]
                                ),
                            ),
                            self.executable.name,
                        )
                    ],
                },
                context=RunContext(
                    model=llm_provider(metadata.model.family, metadata.model.model)
                    if metadata.model
                    else None,
                )
                if metadata
                else None,
                stream_mode=["values", "messages", "tasks"],
                output_keys=self.executable.graph.output_channels,
                subgraphs=True,
            ):
                await relay.handle(namespace, mode, data)
        except GraphRecursionError:
            await updater.failed(_reason(updater, "Ran out of steps before finishing"))
            return
        except ExecuteError as error:
            await updater.failed(_reason(updater, str(error), error.next_step))
            return
        if relay.interrupts:
            await updater.requires_input(
                updater.new_agent_message(
                    [_interrupt_part(i) for i in relay.interrupts]
                )
            )
            return
        if self.executable.kind == "workflow":
            reply = new_data_part(to_jsonable_python(relay.result))
        elif structured := relay.result.get("structured_response"):
            reply = new_data_part(to_jsonable_python(structured))
        else:
            reply = new_text_part(relay.result["messages"][-1].text)
        await updater.add_artifact([reply], name=self.executable.name)
        await updater.complete()

    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Mark the task cancelled once the SDK has stopped the run"""
        await TaskUpdater(event_queue, context.task_id, context.context_id).cancel()
