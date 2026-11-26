from collections.abc import Callable, Sequence
from contextlib import AsyncExitStack
from typing import Any, Literal, override
from zoneinfo import ZoneInfo

from a2a.helpers import (
    get_data_parts,
    new_data_part,
    new_task_from_user_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TaskState
from google.protobuf.json_format import MessageToDict
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import (
    Command,
    Interrupt,
    StateSnapshot,
    TaskPayload,
    TaskResultPayload,
)
from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    ValidationError,
)
from pydantic_core import to_jsonable_python

from src.app.a2a.ownership import Ownership
from src.clients.llm_providers import llm_provider
from src.core.config import Family, get_settings
from src.core.errors import ExecuteError
from src.core.types import NextStep
from src.core.usage import UsageReporter
from src.shared.run_context import RunContext


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


class SentMessage(BaseModel):
    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    created_at: AwareDatetime
    """When the user sent the message"""

    timezone: ZoneInfo | None = None
    """The user's time zone when they sent it, such as Europe/London; None is UTC"""


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

    document_id: str | None = None
    """The document the step's tool call names, if any"""


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
    calls: dict[str, list[tuple[str, str, str | None]]],
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

    def step(
        id: str,
        parent: str | None,
        name: str,
        detail: str | None,
        document_id: str | None = None,
    ) -> Step:
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
            document_id=document_id,
        )

    details = {} if "input" in task else _details(task)
    detail = [*details.values()][-1] if details else None
    if kind == "workflow":
        return [] if namespace else [step(task["id"], None, task["name"], detail)]
    if not namespace and task["name"] == "tools":
        if "input" in task:
            calls[task["id"]] = [
                (
                    call["id"],
                    call["name"],
                    document_id
                    if isinstance(document_id := call["args"].get("document_id"), str)
                    else None,
                )
                for call in task["input"]
            ]
        return [
            step(call_id, None, name, details.get(call_id), document_id)
            for call_id, name, document_id in (
                calls[task["id"]] if "input" in task else calls.pop(task["id"], [])
            )
        ]
    if len(namespace) == 1 and (
        parent := calls.get(namespace[0].removeprefix("tools:"))
    ):
        return [step(task["id"], parent[0][0], task["name"], detail)]
    return []


def _widget_first(interrupts: Sequence[Interrupt]) -> list[Interrupt]:
    """The interrupts with the user's questions before the data requests, so the
    first is the one a bare answer goes to"""
    return sorted(
        interrupts,
        key=lambda pending: (
            isinstance(pending.value, dict) and "execute_tool" in pending.value
        ),
    )


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


class EventRelay:
    def __init__(self, updater: TaskUpdater, executable: Executable) -> None:
        """Turns one run's stream of the executable's graph into the task's events"""
        self.updater = updater
        """Writes the task's events"""

        self.executable = executable
        """The executable whose graph streams"""

        self.result: dict = {}
        """The graph's latest values, from its checkpoint before the run streams any"""

        self.interrupts: list[Interrupt] = []
        """Every pause the run stopped at"""

        self.opened: set[str] = set()
        """The ids of the thinking and text artifacts already streamed"""

        self.calls: dict[str, list[tuple[str, str, str | None]]] = {}
        """Each running tools task's calls, as (call id, tool name, document id)"""

        self.finished: set[str] = set()
        """The top-level tasks that ended before a resume, which LangGraph lists again
        without running them"""

    async def _save_latest_state(self, namespace: tuple[str, ...], data: dict) -> None:
        """Keeps the top-level graph's values and the pauses they carry"""
        if namespace:
            return
        self.interrupts += data.get("__interrupt__", [])
        self.result = data

    async def _stream_reply(
        self, namespace: tuple[str, ...], data: tuple[Any, dict]
    ) -> None:
        """Streams the replying model's thinking and text, one artifact per model
        turn"""
        if tuple(segment.partition(":")[0] for segment in namespace) != (
            (self.executable.reply_node,) if self.executable.reply_node else ()
        ):
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

    async def _report_steps(
        self, namespace: tuple[str, ...], data: TaskPayload | TaskResultPayload
    ) -> None:
        """Reports the steps a graph task starts or ends, then publishes the artifacts
        returned by a top-level tools task's tools or those of a subagent it runs"""
        if not namespace and data["id"] in self.finished:
            return
        for step in _steps(self.executable.kind, namespace, data, self.calls):
            await self.updater.update_status(
                TaskState.TASK_STATE_WORKING,
                self.updater.new_agent_message(
                    [new_data_part({"step": step.model_dump()})]
                ),
            )
        if (
            tuple(segment.partition(":")[0] for segment in namespace)
            not in ((), ("tools",))
            or data["name"] != "tools"
            or "result" not in data
        ):
            return
        for message in data["result"].get("messages", []):
            match message:
                case ToolMessage(artifact={"name": str() as name, "data": artifact}):
                    await self.updater.add_artifact(
                        [new_data_part(to_jsonable_python(artifact))],
                        name=name,
                        append=False,
                    )

    async def handle(self, namespace: tuple[str, ...], mode: str, data: Any) -> None:
        """Relays one streamed chunk with its stream mode's handler"""
        match mode:
            case "values":
                await self._save_latest_state(namespace, data)
            case "messages":
                await self._stream_reply(namespace, data)
            case "tasks":
                await self._report_steps(namespace, data)


class Start:
    resumes = False
    """Whether the run goes on from the thread's latest checkpoint"""

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
                sent = SentMessage.model_validate(MessageToDict(message.metadata))
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
    """Whether the run goes on from the thread's latest checkpoint"""

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
        if paused := next(iter(_widget_first(snapshot.interrupts)), None):
            return Command(
                resume={paused.id: data[0] if data else context.get_user_input()}
            )
        raise ExecuteError("There is no question waiting for an answer")


class Restart:
    resumes = True
    """Whether the run goes on from the thread's latest checkpoint"""

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

REPLIES: tuple[
    tuple[Callable[[Executable, dict], bool], Callable[[dict], Part]], ...
] = (
    (
        lambda executable, values: executable.kind == "workflow",
        lambda values: new_data_part(to_jsonable_python(values)),
    ),
    (
        lambda executable, values: bool(values.get("structured_response")),
        lambda values: new_data_part(to_jsonable_python(values["structured_response"])),
    ),
    (
        lambda executable, values: bool(values["messages"][-1].text.strip()),
        lambda values: new_text_part(values["messages"][-1].text),
    ),
)
"""Each reply a finished run completes with, checked in order, with when it
applies; a run none applies to stopped without replying"""


class LanggraphExecutor(AgentExecutor):
    def __init__(self, executable: Executable, ownership: Ownership) -> None:
        """Runs the executable's graph as one A2A task per run, owning the task
        while it runs"""
        self.executable = executable
        self.ownership = ownership

    async def _forget(self, task_id: str) -> None:
        """Deletes a workflow task's checkpoints once it can no longer resume; an
        agent's thread keeps its state"""
        if self.executable.kind == "workflow" and isinstance(
            checkpointer := self.executable.graph.checkpointer, BaseCheckpointSaver
        ):
            await checkpointer.adelete_thread(task_id)

    async def _fail(
        self, updater: TaskUpdater, reason: str, next_step: NextStep | None = None
    ) -> None:
        """Fails the task with the reason, and what the user must do first when there
        is something"""
        await self.ownership.confirm(updater.task_id)
        await updater.failed(
            updater.new_agent_message(
                [
                    new_text_part(reason),
                    *(
                        [new_data_part({"next": next_step.model_dump()})]
                        if next_step
                        else []
                    ),
                ]
            )
        )
        await self._forget(updater.task_id)

    @override
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Own the task while the run goes on, and give it up once the run stops;
        a run cancelled by a takeover or a shutdown keeps it for the next owner"""
        await self.ownership.claim(context.task_id)
        async with AsyncExitStack() as held:
            try:
                await self._execute(context, event_queue, held)
            except Exception:
                await self.ownership.drop(context.task_id)
                raise
        await self.ownership.drop(context.task_id)

    async def _execute(
        self, context: RequestContext, event_queue: EventQueue, held: AsyncExitStack
    ) -> None:
        """Run, resume or restart the graph, on the model the request metadata names,
        holding an agent's thread in held, and report how it ended"""
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        relay = EventRelay(updater, self.executable)
        invalid = None
        try:
            metadata = RunMetadata.model_validate(context.metadata)
        except ValidationError as error:
            metadata, invalid = RunMetadata(), f"Invalid input: {error}"
        if context.current_task is None and context.message:
            task = new_task_from_user_message(context.message)
            task.metadata.update(
                {
                    "executable": self.executable.name,
                    "run": metadata.model_dump(mode="json", exclude_none=True),
                }
            )
            await event_queue.enqueue_event(task)
        await updater.start_work()
        config: RunnableConfig = {
            "configurable": {
                "thread_id": context.context_id
                if self.executable.kind == "agent"
                else context.task_id
            }
        }
        try:
            if invalid:
                raise ExecuteError(invalid)
            if self.executable.kind == "agent" and not await held.enter_async_context(
                self.ownership.thread(context.context_id)
            ):
                raise ExecuteError(
                    "An earlier message to the assistant is still running"
                )
            strategy = next(
                strategy for applies, strategy in GRAPH_INPUTS if applies(context)
            )
            snapshot = None
            if strategy.resumes:
                snapshot = await self.executable.graph.aget_state(config)
                relay.result = snapshot.values
                relay.finished = {
                    task.id for task in snapshot.tasks if task.result is not None
                }
            graph_input = await strategy.graph_input(self.executable, context, snapshot)
            if metadata.model and not get_settings().offers(
                metadata.model.family, metadata.model.model
            ):
                raise ExecuteError(
                    f"ezcareer-harness does not offer {metadata.model.model} for {metadata.model.family}"
                )
            try:
                async for namespace, mode, data in self.executable.graph.astream(
                    graph_input,
                    {
                        **config,
                        "metadata": {"task_id": context.task_id},
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
                        else None
                    ),
                    stream_mode=["values", "messages", "tasks"],
                    output_keys=self.executable.graph.output_channels,
                    subgraphs=True,
                ):
                    await relay.handle(namespace, mode, data)
            except GraphRecursionError as error:
                raise ExecuteError("Ran out of steps before finishing") from error
            except ExecuteError:
                raise
            except Exception:
                await self.ownership.confirm(context.task_id)
                await self._forget(context.task_id)
                raise
            await self.ownership.confirm(context.task_id)
            if relay.interrupts:
                await updater.requires_input(
                    updater.new_agent_message(
                        [_interrupt_part(i) for i in _widget_first(relay.interrupts)]
                    )
                )
                return
            reply = next(
                (
                    part(relay.result)
                    for applies, part in REPLIES
                    if applies(self.executable, relay.result)
                ),
                None,
            )
            if reply is None:
                raise ExecuteError("The assistant stopped without replying")
        except ExecuteError as error:
            await self._fail(updater, str(error), error.next_step)
            return
        await updater.add_artifact([reply], name=self.executable.name)
        completed = updater.new_agent_message([reply])
        if self.executable.kind == "agent":
            completed.message_id = relay.result["messages"][-1].id
        await updater.complete(completed)
        await self._forget(context.task_id)

    @override
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Mark the task cancelled before the SDK stops its run, and delete a
        workflow's checkpoints; an agent's thread keeps the steps that finished"""
        await TaskUpdater(event_queue, context.task_id, context.context_id).cancel()
        await self._forget(context.task_id)
        await self.ownership.drop(context.task_id)
