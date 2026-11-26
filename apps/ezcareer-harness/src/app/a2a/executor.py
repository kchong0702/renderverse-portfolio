from collections.abc import Callable
from contextlib import AsyncExitStack
from typing import override

from a2a.helpers import new_data_part, new_task_from_user_message, new_text_part
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import Part, TaskState
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphRecursionError
from langgraph.types import Interrupt
from pydantic import BaseModel, ConfigDict, ValidationError
from pydantic_core import to_jsonable_python

from src.app.a2a.event_relay import EventRelay
from src.app.a2a.executable import Executable
from src.app.a2a.graph_inputs import GRAPH_INPUTS, questions_first
from src.app.a2a.task_supervisor import TaskSupervisor
from src.clients.llm_providers import llm_provider
from src.core.config import Family, get_settings
from src.core.errors import ExecuteError
from src.core.types import NextStep
from src.core.usage import UsageReporter
from src.infrastructure.stores import ThreadLock
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


def _interrupt_part(interrupt: Interrupt) -> Part:
    """The interrupt's value as a data part, tagged with the id its answer comes back
    under"""
    part = new_data_part(to_jsonable_python(interrupt.value))
    part.metadata.update({"interrupt_id": interrupt.id})
    return part


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
    def __init__(
        self,
        executable: Executable,
        supervisor: TaskSupervisor,
        thread_lock: ThreadLock,
    ) -> None:
        """Runs the executable's graph as one A2A task per run, owning the task
        while it runs"""
        self.executable = executable
        """The graph this executor runs"""

        self.supervisor = supervisor
        """Owns the task while its run goes on"""

        self.thread_lock = thread_lock
        """Lets one run at a time use an agent's thread"""

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
        await self.supervisor.cancel_if_taken_over(updater.task_id)
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
        await self.supervisor.claim(context.task_id)
        async with AsyncExitStack() as held:
            try:
                await self._execute(context, event_queue, held)
            except Exception:
                await self.supervisor.unclaim(context.task_id)
                raise
        await self.supervisor.unclaim(context.task_id)

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
                self.thread_lock.hold(context.context_id)
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
                await self.supervisor.cancel_if_taken_over(context.task_id)
                await self._forget(context.task_id)
                raise
            await self.supervisor.cancel_if_taken_over(context.task_id)
            if relay.interrupts:
                await updater.requires_input(
                    updater.new_agent_message(
                        [_interrupt_part(i) for i in questions_first(relay.interrupts)]
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
        await self.supervisor.unclaim(context.task_id)
