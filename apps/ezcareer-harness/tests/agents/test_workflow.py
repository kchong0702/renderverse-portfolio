import pytest
from deepagents import HarnessProfileConfig
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from pydantic import BaseModel

from src.agents import Agent, Workflow, build_agent
from tests.agents.test_builder import GREETER, look_up_name
from tests.conftest import ScriptedChatModel


class Greeting(BaseModel):
    text: str


class Farewell(BaseModel):
    text: str


@tool
def look_up_title(person: str) -> str:
    """Looks up a person's title"""
    return "Countess"


def _call(name: str, **args) -> AIMessage:
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": f"call-{name}"}]
    )


def _agent(model: ScriptedChatModel, model_name: str = "glm-5.3"):
    agent = Agent.load(GREETER.model_copy(update={"model": model_name}))
    agent = agent.model_copy(
        update={
            "profile": HarnessProfileConfig(
                tool_description_overrides={"look_up_title": "Finds the title to use"}
            )
        }
    )
    return build_agent(
        agent, answers=(Greeting, Farewell), tools=(look_up_name,), model=model
    )


async def _ask(agent, workflow: Workflow) -> dict:
    return await agent.ainvoke(
        {"messages": [HumanMessage("Lovelace")]}, workflow.config()
    )


@pytest.mark.parametrize("model_name", ["glm-5.3", "gpt-6-luna"])
async def test_one_agent_answers_with_each_workflows_answer(model_name: str):
    model = ScriptedChatModel(
        replies=[_call("Greeting", text="Hello!"), _call("Farewell", text="Bye!")],
        model_name=model_name,
    )
    agent = _agent(model, model_name)

    greeted = await _ask(agent, Workflow(answer=Greeting))
    left = await _ask(agent, Workflow(answer=Farewell))

    assert greeted["structured_response"] == Greeting(text="Hello!")
    assert left["structured_response"] == Farewell(text="Bye!")


async def test_a_workflows_tools_are_offered_described_and_run():
    model = ScriptedChatModel(
        replies=[
            _call("look_up_title", person="Lovelace"),
            _call("Greeting", text="Hi"),
        ]
    )
    seen: list[dict[str, str]] = []
    bind = model.bind_tools

    def record(tools, **kwargs):
        seen.append({t.name: t.description for t in tools if hasattr(t, "name")})
        return bind(tools, **kwargs)

    object.__setattr__(model, "bind_tools", record)

    result = await _ask(
        _agent(model),
        Workflow(
            answer=Greeting,
            tools=(look_up_title,),
            hidden_tools=frozenset({"look_up_name"}),
        ),
    )

    [title] = [
        m
        for m in result["messages"]
        if isinstance(m, ToolMessage) and m.name == "look_up_title"
    ]
    assert title.text == "Countess"
    assert seen[0]["look_up_title"] == "Finds the title to use"
    assert "look_up_name" not in seen[0]


async def test_a_workflow_runs_the_agent_on_its_own_model():
    built_with = ScriptedChatModel(replies=[_call("Greeting", text="from the agent")])
    workflow_model = ScriptedChatModel(
        replies=[_call("Greeting", text="from the workflow")]
    )

    result = await _ask(
        _agent(built_with), Workflow(answer=Greeting, model=workflow_model)
    )

    assert result["structured_response"] == Greeting(text="from the workflow")
    assert built_with.requests == []
