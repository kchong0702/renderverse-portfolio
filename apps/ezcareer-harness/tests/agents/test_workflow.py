import json
from typing import Annotated, Literal, override

import pytest
from deepagents import HarnessProfileConfig
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.agents import Agent, Workflow, answer_of, build_agent
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


def _agent(model, model_name: str = "glm-5.3"):
    agent = Agent.load(GREETER.model_copy(update={"model": model_name}))
    agent = agent.model_copy(
        update={
            "profile": HarnessProfileConfig(
                tool_description_overrides={"look_up_title": "Finds the title to use"}
            )
        }
    )
    return build_agent(agent, tools=(look_up_name,), model=model)


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

    assert answer_of(greeted["messages"], Greeting) == Greeting(text="Hello!")
    assert answer_of(left["messages"], Farewell) == Farewell(text="Bye!")
    assert "Farewell" not in model.offered_tools[0]


async def test_a_valid_answer_ends_the_run():
    model = ScriptedChatModel(
        replies=[_call("Greeting", text="Hi"), _call("look_up_name", person="x")]
    )

    await _ask(_agent(model), Workflow(answer=Greeting))

    assert len(model.requests) == 1


async def test_an_invalid_answer_goes_back_to_the_model_to_retry():
    model = ScriptedChatModel(
        replies=[_call("Greeting", greeting="Hi"), _call("Greeting", text="Hi")]
    )

    result = await _ask(_agent(model), Workflow(answer=Greeting))

    [error] = [
        m
        for m in result["messages"]
        if isinstance(m, ToolMessage) and m.status == "error"
    ]
    assert error.name == "Greeting"
    assert answer_of(result["messages"], Greeting) == Greeting(text="Hi")
    assert len(model.requests) == 2


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

    assert answer_of(result["messages"], Greeting) == Greeting(text="from the workflow")
    assert built_with.requests == []


class _RecordingOpenAI(ChatOpenAI):
    sent: list[list[dict]] = Field(default_factory=list)
    answer: dict = Field(
        default_factory=lambda: {"name": "Greeting", "args": {"text": "Hi"}}
    )

    @override
    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        self.sent.append(kwargs["tools"])
        message = AIMessage("", tool_calls=[{**self.answer, "id": "c1"}])
        return ChatResult(generations=[ChatGeneration(message=message)])


async def test_openai_models_get_the_answer_tool_in_strict_mode():
    model = _RecordingOpenAI(model="gpt-test", api_key="test")

    result = await _ask(_agent(model), Workflow(answer=Greeting))

    tools = {t["function"]["name"]: t["function"] for t in model.sent[0]}
    assert tools["Greeting"]["strict"] is True
    assert not tools["look_up_name"].get("strict")
    assert answer_of(result["messages"], Greeting) == Greeting(text="Hi")


class _Wave(BaseModel):
    kind: Literal["wave"]


class _Bow(BaseModel):
    kind: Literal["bow"]


class Gesture(BaseModel):
    gestures: list[Annotated[_Wave | _Bow, Field(discriminator="kind")]]


async def test_openai_models_get_anyof_where_the_answer_schema_has_oneof():
    model = _RecordingOpenAI(
        model="gpt-test",
        api_key="test",
        answer={"name": "Gesture", "args": {"gestures": [{"kind": "wave"}]}},
    )

    await _ask(_agent(model), Workflow(answer=Gesture))

    [sent] = [t for t in model.sent[0] if t["function"]["name"] == "Gesture"]
    assert "oneOf" in json.dumps(Gesture.model_json_schema())
    assert "oneOf" not in json.dumps(sent)
    assert "anyOf" in json.dumps(sent)


async def test_a_workflow_can_send_its_answer_tool_to_openai_without_strict_mode():
    model = _RecordingOpenAI(model="gpt-test", api_key="test")

    await _ask(_agent(model), Workflow(answer=Greeting, strict=False))

    [sent] = [t for t in model.sent[0] if t["function"]["name"] == "Greeting"]
    assert not sent["function"].get("strict")
