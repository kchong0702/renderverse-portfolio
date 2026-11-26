from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.app.a2a import LanggraphExecutor
from src.app.threads.schemas import SummaryEdit, ThreadSummary

router = APIRouter(prefix="/threads", tags=["threads"])


def get_executor(
    request: Request, agent: Literal["career-director", "career-consultant"]
) -> LanggraphExecutor:
    """The executor that runs the agent's graph, which keeps each thread's state"""
    return request.app.state.handlers[agent].agent_executor


@router.get("/{thread_id}/summary")
async def read_summary(
    thread_id: str, executor: Annotated[LanggraphExecutor, Depends(get_executor)]
) -> ThreadSummary:
    """The whole summary message of the thread's older messages its agent made, or
    None"""
    state = await executor.executable.graph.aget_state(
        {"configurable": {"thread_id": thread_id}}
    )
    event = state.values.get("_summarization_event")
    return ThreadSummary(summary=event["summary_message"].text if event else None)


@router.put("/{thread_id}/summary")
async def edit_summary(
    thread_id: str,
    edit: SummaryEdit,
    executor: Annotated[LanggraphExecutor, Depends(get_executor)],
) -> ThreadSummary:
    """Replaces the whole summary message of the thread, which its agent sees from
    its next model call; refused while a run holds the thread or it waits to go on"""
    graph = executor.executable.graph
    config = {"configurable": {"thread_id": thread_id}}
    async with executor.thread_lock.hold(thread_id, wait=False) as held:
        snapshot = await graph.aget_state(config)
        if not held or snapshot.next:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "The assistant is answering or waiting for an answer in this thread",
            )
        event = snapshot.values.get("_summarization_event")
        if event is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "The thread has no summary yet"
            )
        await graph.aupdate_state(
            config,
            {
                "_summarization_event": {
                    **event,
                    "summary_message": event["summary_message"].model_copy(
                        update={"content": edit.summary}
                    ),
                }
            },
        )
    return ThreadSummary(summary=edit.summary)
