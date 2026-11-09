from pathlib import Path

import pytest

from src.agents import Agent
from src.core.config import AgentSettings

PROFILE = Path(__file__).parent / "fixtures" / "greeter" / "profile.yaml"


def _load(path: Path = PROFILE, family: str = "claude") -> Agent:
    return Agent.load(
        AgentSettings(name="greeter", path=path, family=family, model="claude-opus-5-5")
    )


def test_an_agent_runs_on_the_family_and_model_its_settings_name():
    agent = _load()

    assert (agent.family, agent.model) == ("claude", "claude-opus-5-5")
    assert "write_file" in agent.profile.excluded_tools


def test_an_agent_reads_the_prompt_and_skills_its_profile_names(tmp_path: Path):
    profile = tmp_path / "profile.yaml"
    profile.write_text("system_prompt: prompts/main.md\nskills: shared\n")

    agent = _load(profile)

    assert agent.system_prompt == tmp_path / "prompts/main.md"
    assert agent.skills == tmp_path / "shared"


def test_a_profile_that_names_neither_reads_them_beside_it(tmp_path: Path):
    profile = tmp_path / "profile.yaml"
    profile.write_text("excluded_tools: [task]\n")

    agent = _load(profile)

    assert agent.system_prompt == tmp_path / "system.md"
    assert agent.skills == tmp_path / "skills"


def test_an_unknown_model_family_is_refused():
    with pytest.raises(ValueError, match="unknown model family gpt"):
        _load(family="gpt")
