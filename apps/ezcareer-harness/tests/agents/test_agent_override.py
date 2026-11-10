from typing import Annotated, TypedDict

import pytest
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from src.agents import Agent, AgentOverride, build_agent
from tests.agents.test_builder import GREETER, _call, look_up_name, look_up_title
from tests.conftest import ScriptedChatModel


class Greeting(BaseModel):
    text: str


class Farewell(BaseModel):
    text: str


def _agent(model: ScriptedChatModel, model_name: str = "glm-5.3") -> CompiledStateGraph:
    agent = Agent.load(GREETER.model_copy(update={"model": model_name}))
    agent = agent.model_copy(
        update={
            "profile": agent.profile.model_copy(
                update={
                    "tool_description_overrides": {
                        "look_up_title": "Finds the title to use"
                    }
                }
            )
        }
    )
    return build_agent(
        agent,
        response_formats=(Greeting, Farewell),
        tools=(look_up_name, look_up_title),
        model=model,
    )


async def _ask(agent: CompiledStateGraph, override: AgentOverride) -> dict:
    return await agent.ainvoke(
        {"messages": [HumanMessage("Lovelace")]}, override.config()
    )


@pytest.mark.parametrize("model_name", ["glm-5.3", "gpt-6-luna"])
async def test_one_agent_replies_in_each_overrides_response_format(model_name: str):
    model = ScriptedChatModel(
        replies=[_call("Greeting", text="Hello!"), _call("Farewell", text="Bye!")],
        model_name=model_name,
    )
    agent = _agent(model, model_name)

    greeted = await _ask(agent, AgentOverride(response_format=Greeting))
    left = await _ask(agent, AgentOverride(response_format=Farewell))

    assert greeted["structured_response"] == Greeting(text="Hello!")
    assert left["structured_response"] == Farewell(text="Bye!")
    assert "Farewell" not in model.offered_tools[0]


async def test_a_model_without_native_output_is_offered_only_the_calls_answer_tool():
    model = ScriptedChatModel(
        replies=[_call("Greeting", text="Hello!"), _call("Farewell", text="Bye!")]
    )
    agent = _agent(model)

    greeted = await _ask(agent, AgentOverride(response_format=Greeting))
    left = await _ask(agent, AgentOverride(response_format=Farewell))

    assert [tools & {"Greeting", "Farewell"} for tools in model.offered_tools] == [
        {"Greeting"},
        {"Farewell"},
    ]
    assert model.answer_name is None
    assert greeted["structured_response"] == Greeting(text="Hello!")
    assert left["structured_response"] == Farewell(text="Bye!")


async def test_a_valid_answer_ends_the_run():
    model = ScriptedChatModel(
        replies=[_call("Greeting", text="Hi"), _call("look_up_name", person="x")]
    )

    await _ask(_agent(model), AgentOverride(response_format=Greeting))

    assert len(model.requests) == 1


async def test_an_invalid_answer_goes_back_to_the_model_to_retry():
    model = ScriptedChatModel(
        replies=[_call("Greeting", greeting="Hi"), _call("Greeting", text="Hi")]
    )

    result = await _ask(_agent(model), AgentOverride(response_format=Greeting))

    feedback = model.requests[1][-1]
    assert isinstance(feedback, ToolMessage)
    assert feedback.name == "Greeting"
    assert "text" in feedback.text
    assert result["structured_response"] == Greeting(text="Hi")
    assert len(model.requests) == 2


async def test_an_override_offers_only_the_tools_it_allows():
    model = ScriptedChatModel(
        replies=[
            _call("look_up_title", person="Lovelace"),
            _call("Greeting", text="Hi"),
        ]
    )

    result = await _ask(
        _agent(model),
        AgentOverride(response_format=Greeting, tools=frozenset({"look_up_title"})),
    )

    assert "look_up_title" in model.offered_tools[0]
    assert "look_up_name" not in model.offered_tools[0]
    assert model.tool_descriptions["look_up_title"] == "Finds the title to use"
    assert result["structured_response"] == Greeting(text="Hi")


async def test_an_override_that_allows_a_tool_the_agent_lacks_fails():
    model = ScriptedChatModel(replies=[_call("Greeting", text="Hi")])

    with pytest.raises(ValueError, match="look_up_age"):
        await _ask(
            _agent(model),
            AgentOverride(response_format=Greeting, tools=frozenset({"look_up_age"})),
        )


async def test_an_override_leaves_out_a_skill_tool_it_doesnt_allow():
    model = ScriptedChatModel(
        replies=[
            _call("read_file", file_path="/title/SKILL.md"),
            _call("Greeting", text="Hi"),
        ]
    )
    agent = build_agent(
        Agent.load(GREETER),
        response_formats=(Greeting,),
        tools=(look_up_name,),
        skill_tools=(look_up_title,),
        model=model,
    )

    await _ask(
        agent,
        AgentOverride(response_format=Greeting, tools=frozenset({"look_up_name"})),
    )

    assert "look_up_title" not in model.offered_tools[1]


async def test_an_agent_called_without_an_override_replies_in_text():
    model = ScriptedChatModel(replies=[AIMessage("Hello, Ada!")])

    result = await _agent(model).ainvoke({"messages": [HumanMessage("Lovelace")]})

    assert result["messages"][-1].text == "Hello, Ada!"
    assert result["structured_response"] is None
    assert not {"Greeting", "Farewell"} & model.offered_tools[0]


class _Greeted(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    structured_response: Greeting


def _graph(agent: CompiledStateGraph) -> CompiledStateGraph:
    graph = StateGraph(_Greeted)
    graph.add_node(
        "agent",
        agent.with_config(AgentOverride(response_format=Greeting).config()),
    )
    graph.add_edge(START, "agent")
    graph.add_edge("agent", END)
    return graph.compile()


async def test_an_agent_added_as_a_graph_node_answers_in_the_nodes_override():
    model = ScriptedChatModel(
        replies=[
            _call("look_up_title", person="Lovelace"),
            _call("Greeting", text="Hi"),
        ]
    )

    result = await _graph(_agent(model)).ainvoke(
        {"messages": [HumanMessage("Lovelace")]}
    )

    assert result["structured_response"] == Greeting(text="Hi")
    assert "look_up_title" in model.offered_tools[0]


async def test_an_agent_added_as_a_graph_node_runs_under_the_graphs_recursion_limit():
    model = ScriptedChatModel(replies=[_call("look_up_name", person="Lovelace")])

    with pytest.raises(GraphRecursionError):
        await (
            _graph(_agent(model))
            .with_config(recursion_limit=6)
            .ainvoke({"messages": [HumanMessage("Lovelace")]})
        )

    assert len(model.requests) < 6
