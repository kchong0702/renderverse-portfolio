import re
from pathlib import Path

import yaml
from dependency_injector import providers

from src.agents import Agent
from src.app.container import Container


def _names(value: object) -> set[str]:
    tools = value() if isinstance(value, providers.Provider) else value or ()
    return {tool.name for tool in tools}


def _served() -> dict[str, tuple[Agent, set[str], set[str]]]:
    container = Container()
    built = [
        container.job_finder.agent,
        container.career_consultant.agent,
        container.career_director.agent,
        container.import_document.agent,
    ]
    return {
        agent.name: (
            agent,
            _names(provider.kwargs.get("tools")),
            _names(provider.kwargs.get("skill_tools")),
        )
        for provider in built
        for agent in [provider.kwargs["agent"]()]
    }


def _everyone(served: dict[str, tuple[Agent, set[str], set[str]]]) -> set[str]:
    return {
        name
        for _, tools, skill_tools in served.values()
        for name in tools | skill_tools
    }


def _skill_files(agent: Agent) -> list[Path]:
    return sorted(agent.skills.glob("*/SKILL.md")) if agent.skills.is_dir() else []


def _included(skill: Path) -> set[str]:
    metadata = yaml.safe_load(skill.read_text().split("---")[1]).get("metadata") or {}
    return set(metadata.get("include_tools", "").split())


def tool_gaps(
    agent: Agent, tools: set[str], skill_tools: set[str], everyone: set[str]
) -> list[str]:
    """Each tool agent's prompt or skills name, or its skills include, that it
    doesn't have, and each skill tool no skill includes"""
    texts = [agent.system_prompt, *_skill_files(agent)]
    named = {
        name for text in texts for name in re.findall(r"`(\w+)`", text.read_text())
    }
    included = {name for skill in _skill_files(agent) for name in _included(skill)}
    return sorted(
        [
            f"{agent.name} names {name}"
            for name in named & everyone - tools - skill_tools
        ]
        + [
            f"{agent.name} includes {name}, not one of its skill tools"
            for name in included - skill_tools
        ]
        + [f"{agent.name} never offers {name}" for name in skill_tools - included]
    )


def test_every_tool_an_agent_names_is_its_own(isolate_env):
    served = _served()
    everyone = _everyone(served)

    assert [
        gap
        for agent, tools, skill_tools in served.values()
        for gap in tool_gaps(agent, tools, skill_tools, everyone)
    ] == []


def test_the_check_catches_a_tool_an_agent_lacks(isolate_env):
    served = _served()
    job_finder, tools, _ = served["job-finder"]
    everyone = _everyone(served)

    assert tool_gaps(job_finder, tools, set(), everyone) == [
        "job-finder includes search_jobs, not one of its skill tools",
        "job-finder names search_jobs",
    ]
    assert tool_gaps(job_finder, tools, {"search_jobs", "rank_jobs"}, everyone) == [
        "job-finder never offers rank_jobs"
    ]
