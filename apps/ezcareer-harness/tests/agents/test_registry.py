from pathlib import Path

import pytest

from src.agents import Agent
from src.core.config import _ROOT_PATH, AgentSettings

PROFILE = Path(__file__).parent / "fixtures" / "greeter" / "profile.yaml"


def _load(path: Path = PROFILE, family: str = "claude") -> Agent:
    return Agent.load(
        AgentSettings(name="greeter", path=path, family=family, model="claude-opus-5-5")
    )


def test_an_agent_runs_on_the_family_and_model_its_settings_name():
    agent = _load()

    assert (agent.family, agent.model) == ("claude", "claude-opus-5-5")


def test_an_agent_reads_the_prompt_and_skills_its_profile_names_from_the_app_folder(
    tmp_path: Path,
):
    profile = tmp_path / "profile.yaml"
    profile.write_text(
        "system_prompt: src/agents/job_finder/system.md\n"
        "skills: src/agents/job_finder/skills\n"
    )

    agent = _load(profile)

    assert agent.system_prompt == _ROOT_PATH / "src/agents/job_finder/system.md"
    assert agent.skills == _ROOT_PATH / "src/agents/job_finder/skills"


def test_a_profile_that_names_neither_reads_them_beside_it():
    agent = _load()

    assert agent.system_prompt == PROFILE.parent / "system.md"
    assert agent.skills == PROFILE.parent / "skills"


def test_an_unknown_model_family_is_refused():
    with pytest.raises(ValueError, match="Input should be 'claude', 'glm' or 'openai'"):
        _load(family="gpt")
