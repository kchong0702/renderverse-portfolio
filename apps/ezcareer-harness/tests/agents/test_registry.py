from pathlib import Path

import pytest

from src.agents import Agent
from src.core.config import AgentSettings

PROFILE = Path(__file__).parent / "fixtures" / "greeter" / "profile.yaml"


def _load(model: str, path: Path = PROFILE) -> Agent:
    return Agent.load(AgentSettings(name="greeter", path=path, model=model))


def test_an_agent_runs_on_the_family_its_profile_lists_the_model_under():
    agent = _load("claude-opus-5-5")

    assert agent.family == "claude"
    assert "write_file" in agent.profile.excluded_tools


def test_an_agent_reads_its_prompt_and_skills_beside_its_profile_by_default():
    agent = _load("glm-5.3")

    assert agent.system_prompt == PROFILE.parent / "system.md"
    assert agent.skills == PROFILE.parent / "skills"


def test_a_profile_can_name_its_own_prompt_and_skills(tmp_path: Path):
    profile = tmp_path / "profile.yaml"
    profile.write_text(
        "system_prompt: prompts/main.md\nskills: shared\nmodels:\n  glm: [glm-5.3]\n"
    )

    agent = _load("glm-5.3", profile)

    assert agent.system_prompt == tmp_path / "prompts/main.md"
    assert agent.skills == tmp_path / "shared"


def test_a_model_the_profile_does_not_list_is_refused():
    with pytest.raises(ValueError, match="must list gpt-9 under exactly one family"):
        _load("gpt-9")
