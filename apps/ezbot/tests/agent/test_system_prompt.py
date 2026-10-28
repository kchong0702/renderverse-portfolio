from datetime import date
from types import SimpleNamespace

import pytest
from langchain_core.messages import HumanMessage

from src.core.agent.graph import PROMPT_PATH, build_ezbot_graph
from src.core.agent.middlewares.system_prompt import system_prompt_middleware
from src.core.config import IntentSettings
from src.shared.prompt_utils import PromptTemplate, load_prompt
from src.shared.schemas.agent import EzbotContext
from tests.fakes import EchoChatModel


@pytest.mark.parametrize("enabled", [True, False])
def test_ezbot_prompt_mentions_buttons_only_when_intent_is_on(enabled):
    prompt = PromptTemplate(load_prompt(PROMPT_PATH), intent_enabled=enabled)

    text = prompt.render({"today": "2026-10-25"})

    assert load_prompt(PROMPT_PATH).status == "active"
    assert text.startswith("You are Ezbot")
    assert text.endswith("Today's date is 2026-10-25.")
    assert ("button to the relevant part of the room" in text) is enabled
    assert "{%" not in text and "\n\n\n" not in text


def test_runtime_values_prefer_the_agent_state_over_the_context():
    middleware = system_prompt_middleware(PROMPT_PATH, intent_enabled=False)
    context = EzbotContext(today=date(2026, 10, 25))

    def rendered(state: dict) -> str:
        request = SimpleNamespace(
            state=state,
            runtime=SimpleNamespace(context=context),
            override=lambda system_message: system_message,
        )
        return middleware.wrap_model_call(request, lambda r: r).text

    assert rendered({}).endswith("Today's date is 2026-10-25.")
    assert rendered({"today": "updated by a node"}).endswith(
        "Today's date is updated by a node."
    )


async def test_graph_renders_the_prompt_before_each_model_call():
    model = EchoChatModel()
    graph = build_ezbot_graph([model], intent=IntentSettings())

    await graph.ainvoke(
        {"messages": [HumanMessage("hi")]},
        context=EzbotContext(today=date(2026, 10, 25)),
    )

    system = model.calls[0][0]
    assert system.type == "system"
    assert system.text.endswith("Today's date is 2026-10-25.")
