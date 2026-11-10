import json

import httpx2
import pytest
from langchain_core.messages import HumanMessage

from src.agents import Agent, build_agent
from src.clients.llm_providers import llm_provider
from tests.agents.test_builder import GREETER, look_up_name, look_up_title

READ_SKILL = {"file_path": "/title/SKILL.md"}

ANTHROPIC_REPLIES = [
    [
        {
            "type": "tool_use",
            "id": "toolu_1",
            "name": "read_file",
            "input": READ_SKILL,
        }
    ],
    [{"type": "text", "text": "Hello, Countess!"}],
]

OPENAI_REPLIES = [
    [
        {
            "type": "function_call",
            "id": "fc_1",
            "call_id": "call_1",
            "name": "read_file",
            "arguments": json.dumps(READ_SKILL),
            "status": "completed",
        }
    ],
    [
        {
            "type": "message",
            "id": "msg_1",
            "role": "assistant",
            "status": "completed",
            "content": [
                {"type": "output_text", "text": "Hello, Countess!", "annotations": []}
            ],
        }
    ],
]


class FakeProvider:
    def __init__(self, family: str) -> None:
        """Answers each model call with the next scripted reply, keeping each request"""
        self.family = family
        """claude or openai"""

        self.bodies: list[str] = []
        """Every request body, in order"""

    async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
        """Records the request and returns the next reply as the provider would"""
        self.bodies.append(request.content.decode())
        model = json.loads(request.content)["model"]
        usage = {"input_tokens": 1, "output_tokens": 1}
        if self.family == "claude":
            content = ANTHROPIC_REPLIES[len(self.bodies) - 1]
            return httpx2.Response(
                200,
                json={
                    "id": "msg-1",
                    "type": "message",
                    "role": "assistant",
                    "model": model,
                    "content": content,
                    "stop_reason": "tool_use" if len(self.bodies) == 1 else "end_turn",
                    "stop_sequence": None,
                    "usage": usage,
                },
            )
        return httpx2.Response(
            200,
            json={
                "id": "resp-1",
                "object": "response",
                "created_at": 0,
                "status": "completed",
                "model": model,
                "output": OPENAI_REPLIES[len(self.bodies) - 1],
                "parallel_tool_calls": True,
                "tool_choice": "auto",
                "tools": [],
                "usage": {**usage, "total_tokens": 2},
            },
        )


def _offered(body: str) -> set[str]:
    """Names of the tools a request defines, bound or added mid-conversation"""
    request = json.loads(body)
    found = {tool["name"] for tool in request.get("tools", [])}
    for item in request.get("messages") or request["input"]:
        if item.get("type") == "additional_tools":
            found.update(tool["name"] for tool in item["tools"])
        if isinstance(item.get("content"), list):
            found.update(
                block["tool"]["definition"]["name"]
                for block in item["content"]
                if block.get("type") == "tool_addition"
            )
    return found


@pytest.mark.parametrize(
    ("family", "model"), [("claude", "claude-sonnet-5-5"), ("openai", "gpt-6-luna")]
)
async def test_a_provider_is_sent_a_skill_tool_only_after_the_skill_is_read(
    family: str, model: str, monkeypatch: pytest.MonkeyPatch
):
    fake = FakeProvider(family)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setattr(
        httpx2.AsyncHTTPTransport, "handle_async_request", fake.handle_async_request
    )
    agent = build_agent(
        Agent.load(GREETER),
        tools=(look_up_name,),
        skill_tools=(look_up_title,),
        model=llm_provider(family, model),
    )

    await agent.ainvoke({"messages": [HumanMessage("Greet Lovelace")]})

    assert ["look_up_title" in _offered(body) for body in fake.bodies] == [False, True]
