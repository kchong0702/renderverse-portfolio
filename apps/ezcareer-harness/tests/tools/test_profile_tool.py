from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel

from src.agents import Agent, AgentOverride, build_agent
from src.agents.state import ProfileState
from src.shared.profile import ProfileFact
from src.tools import read_profile_facts
from tests.agents.test_builder import GREETER
from tests.conftest import ScriptedChatModel


class Done(BaseModel):
    ok: bool


def _call(name: str, **args) -> AIMessage:
    return AIMessage(
        content="", tool_calls=[{"name": name, "args": args, "id": f"call-{name}"}]
    )


async def test_agent_reads_the_facts_passed_with_the_run():
    model = ScriptedChatModel(
        replies=[_call("read_profile_facts"), _call("Done", ok=True)]
    )
    agent = build_agent(
        Agent.load(GREETER),
        response_formats=(Done,),
        tools=(read_profile_facts,),
        state_schema=ProfileState,
        model=model,
    )

    result = await agent.ainvoke(
        {
            "messages": [HumanMessage("What do I know?")],
            "facts": [
                ProfileFact(
                    id="acme",
                    text="Backend engineer at Acme",
                    start="2019-01",
                    end="present",
                ),
                ProfileFact(id="pg", text="Tuned PostgreSQL queries"),
            ],
        },
        AgentOverride(response_format=Done).config(),
    )

    [listing] = [
        m
        for m in result["messages"]
        if isinstance(m, ToolMessage) and m.name == "read_profile_facts"
    ]
    assert listing.text == (
        "fact:acme  (2019-01 to present) Backend engineer at Acme\n"
        "fact:pg  Tuned PostgreSQL queries"
    )
