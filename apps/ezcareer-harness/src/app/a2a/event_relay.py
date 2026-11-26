from typing import Any

from a2a.helpers import new_data_part, new_text_part
from a2a.server.tasks import TaskUpdater
from a2a.types import TaskState
from langchain_core.messages import AIMessage, ToolCall, ToolMessage
from langgraph.types import Interrupt, TaskPayload, TaskResultPayload
from pydantic_core import to_jsonable_python

from src.app.a2a.executable import Executable
from src.app.a2a.steps import graph_task_steps


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

        self.calls: dict[str, list[ToolCall]] = {}
        """Each running tools task's tool calls, by the task's id"""

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
        for step in graph_task_steps(self.executable.kind, namespace, data, self.calls):
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
