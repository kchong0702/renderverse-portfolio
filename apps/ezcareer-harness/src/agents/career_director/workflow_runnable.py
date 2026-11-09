from functools import partial

from deepagents import DeepAgentState
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph.state import CompiledStateGraph
from pydantic import ValidationError
from pydantic_core import to_json

from src.agents.career_director.state import CareerDirectorState
from src.core.errors import ExecuteError


async def _run_workflow(
    graph: CompiledStateGraph, field: str | None, state: CareerDirectorState
) -> DeepAgentState:
    """Runs graph on the input career-director's state fills, with the task's
    description as its message and as field, and reports its output or why it failed"""
    schema = graph.get_input_schema()
    given = {**state, **({field: state["messages"][-1].text} if field else {})}
    try:
        output = await graph.ainvoke(
            schema.model_validate(
                {name: given[name] for name in schema.model_fields if name in given}
            )
        )
    except (ValidationError, ExecuteError) as error:
        return {"messages": [AIMessage(f"Failed: {error}")]}
    return {"messages": [AIMessage(to_json(output).decode())]}


def workflow_runnable(graph: CompiledStateGraph, field: str | None = None) -> Runnable:
    """graph as a subagent career-director's task tool runs; the task's description
    fills the input field, when given"""
    return RunnableLambda(partial(_run_workflow, graph, field))
