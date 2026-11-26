from collections.abc import Callable
from typing import Literal

from langchain_core.messages import ToolCall, ToolMessage
from langgraph.types import TaskPayload, TaskResultPayload
from pydantic import BaseModel, ConfigDict

from src.shared.tool_artifact import StepDetail

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

    document_id: str | None = None
    """The document the step works on: the one its tool call names, or once done,
    the one its tool reports"""


def _tool_details(task: TaskResultPayload) -> dict[str, StepDetail]:
    """The step details each tool call in the task's result returned, by call id"""
    return {
        message.tool_call_id: message.artifact
        for message in task["result"].get("messages", [])
        if isinstance(message, ToolMessage) and isinstance(message.artifact, dict)
    }


def graph_task_steps(
    kind: Literal["workflow", "agent"],
    namespace: tuple[str, ...],
    task: TaskPayload | TaskResultPayload,
    calls: dict[str, list[ToolCall]],
) -> list[Step]:
    """The steps a graph task starts or ends: an agent's tool calls and the nodes of
    the workflows they run, or a workflow's own nodes, with the details tools set"""
    if "." in task["name"]:
        return []
    details = {} if "input" in task else _tool_details(task)
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
        detail: StepDetail,
        doc_id: object = None,
    ) -> Step:
        """The step with the status STEP_STATUSES gives it, and the detail and the
        document its tool reported; the task's own step fails on any tool error"""
        tool_failed = bool(tool_errors) if id == task["id"] else id in tool_errors
        doc_id = detail.get("step_document_id", doc_id)
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
            detail=detail.get("step_detail"),
            document_id=doc_id if isinstance(doc_id, str) else None,
        )

    set_details = [d["step_detail"] for d in details.values() if "step_detail" in d]
    last_detail: StepDetail = {"step_detail": set_details[-1]} if set_details else {}
    if kind == "workflow":
        return [] if namespace else [step(task["id"], None, task["name"], last_detail)]
    if not namespace and task["name"] == "tools":
        if "input" in task:
            calls[task["id"]] = task["input"]
        tool_calls = calls[task["id"]] if "input" in task else calls.pop(task["id"], [])
        return [
            step(
                call["id"],
                None,
                call["name"],
                details.get(call["id"], {}),
                call["args"].get("document_id"),
            )
            for call in tool_calls
        ]
    if len(namespace) == 1 and (
        parent := calls.get(namespace[0].removeprefix("tools:"))
    ):
        return [step(task["id"], parent[0]["id"], task["name"], last_detail)]
    return []
