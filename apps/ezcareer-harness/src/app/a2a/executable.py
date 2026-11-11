from time import monotonic
from typing import Any, Literal, override
from uuid import UUID

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
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, LLMResult
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, TaskPayload, TaskResultPayload
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    SecretStr,
    ValidationError,
)
from pydantic_core import to_jsonable_python

from src.clients.llm_providers import llm_provider
from src.core.config import Family, get_settings
from src.core.errors import ExecuteError
from src.core.types import NextStep
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


class JSearchKey(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    api_key: SecretStr
    """The user's own RapidAPI key for JSearch"""


class RunMetadata(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        use_attribute_docstrings=True,
    )

    model: ModelChoice | None = None
    """The model the user picked for the run; None keeps each agent's own"""

    jsearch: JSearchKey | None = None
    """The user's JSearch key; None searches on the server's"""


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


class Usage(BaseModel):
    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    provider: str
    """The model's family in [models], else LangChain's ls_provider"""

    model: str
    """The model the call asked for, as [models] names it"""

    agent: str
    """The configured agent whose graph made the call, else the executable"""

    node: str
    """The graph node that made the call"""

    input_tokens: int
    """Input tokens, cache reads and writes included"""

    output_tokens: int
    """Output tokens, reasoning included"""

    cache_read_tokens: int
    """Input tokens read from the prompt cache"""

    cache_write_tokens: int
    """Input tokens written to the prompt cache"""

    reasoning_tokens: int
    """Output tokens spent reasoning"""

    latency_ms: int
    """Time from the call's start to its end"""

    stop_reason: str | None
    """Why the provider stopped, such as end_turn or stop"""

    request_id: str | None
    """The provider's id for the response, such as resp_..."""


class UsageReporter(AsyncCallbackHandler):
    def __init__(self, updater: TaskUpdater, executable: str) -> None:
        """Sends each finished chat model call's usage as a working status update"""
        self.updater = updater
        self.executable = executable
        self.chains: dict[UUID, tuple[str | None, UUID | None]] = {}
        self.calls: dict[UUID, tuple[float, str, dict[str, Any]]] = {}

    @override
    async def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Notes the chain's name and parent, such as an agent's graph"""
        self.chains[run_id] = (kwargs.get("name"), parent_run_id)

    @override
    async def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Notes when the call started, and the nearest agent graph it runs in"""
        agents = {agent.name for agent in get_settings().agents}
        chain = parent_run_id
        while chain in self.chains and self.chains[chain][0] not in agents:
            chain = self.chains[chain][1]
        self.calls[run_id] = (
            monotonic(),
            self.chains[chain][0] if chain in self.chains else self.executable,
            metadata or {},
        )

    @override
    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Sends the call's usage, read from its final AIMessage"""
        started, agent, metadata = self.calls.pop(run_id)
        match response.generations[0][0]:
            case ChatGeneration(
                message=AIMessage(usage_metadata=usage, response_metadata=meta)
            ):
                model = metadata["ls_model_name"]
                tokens = usage or UsageMetadata(
                    input_tokens=0, output_tokens=0, total_tokens=0
                )
                inputs = tokens.get("input_token_details", {})
                outputs = tokens.get("output_token_details", {})
                await self.updater.update_status(
                    TaskState.TASK_STATE_WORKING,
                    self.updater.new_agent_message(
                        [
                            new_data_part(
                                {
                                    "usage": Usage(
                                        provider=next(
                                            (
                                                family
                                                for family, names in get_settings().models.items()
                                                if model in names
                                            ),
                                            metadata["ls_provider"],
                                        ),
                                        model=model,
                                        agent=agent,
                                        node=metadata["langgraph_node"],
                                        input_tokens=tokens["input_tokens"],
                                        output_tokens=tokens["output_tokens"],
                                        cache_read_tokens=inputs.get("cache_read", 0),
                                        cache_write_tokens=inputs.get(
                                            "cache_creation", 0
                                        ),
                                        reasoning_tokens=outputs.get("reasoning", 0),
                                        latency_ms=round(
                                            (monotonic() - started) * 1000
                                        ),
                                        stop_reason=meta.get("stop_reason")
                                        or meta.get("finish_reason")
                                        or meta.get("status"),
                                        request_id=meta.get("id"),
                                    ).model_dump()
                                }
                            )
                        ]
                    ),
                )


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
    agent_nodes: frozenset[str],
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
    if not namespace and task["name"] in agent_nodes and "result" in task:
        return [
            Step(id=call_id, parent=None, name=name, status=status, detail=detail)
            for tools in [*calls]
            for call_id, name in calls.pop(tools)
            if (detail := details.get(call_id))
        ]
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
            for call_id, name in (
                calls[task["id"]] if "input" in task else calls.pop(task["id"], [])
            )
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

    agent_nodes: frozenset[str] = frozenset()
    """The nodes of an agent's handoff graph that each run an agent; whichever
    runs streams its steps, thinking and text as the agent's own"""


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
                    },
                    "callbacks": [UsageReporter(updater, self.executable.name)],
                },
                context=RunContext(
                    model=llm_provider(metadata.model.family, metadata.model.model)
                    if metadata.model
                    else None,
                    jsearch_api_key=metadata.jsearch and metadata.jsearch.api_key,
                )
                if metadata
                else None,
                stream_mode=["values", "messages", "tasks"],
                output_keys=self.executable.graph.output_channels,
                subgraphs=True,
            ):
                if mode == "values" and not namespace:
                    result = data
                    continue
                if namespace and (
                    namespace[0].partition(":")[0] in self.executable.agent_nodes
                ):
                    namespace = namespace[1:]
                if mode == "messages" and tuple(
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
                    for step in _steps(
                        self.executable.kind,
                        namespace,
                        data,
                        calls,
                        self.executable.agent_nodes,
                    ):
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
            await updater.failed(_reason(updater, str(error), error.next_step))
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
