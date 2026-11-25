import shutil
from pathlib import Path

import pytest

from src.agents import Agent
from src.agents.registry import AgentProfile
from src.core.config import _ROOT_PATH, AgentSettings

PROFILE = Path(__file__).parent / "fixtures" / "greeter" / "profile.yaml"


class GreeterProfile(AgentProfile):
    greeting: str = "Hello"
    """What the greeter says first"""


def _load(
    path: Path = PROFILE,
    family: str = "claude",
    profile_type: type[AgentProfile] = AgentProfile,
) -> Agent:
    return Agent.load(
        AgentSettings(
            name="greeter", path=path, family=family, model="claude-opus-5-5"
        ),
        profile_type,
    )


def test_an_agent_runs_on_the_family_and_model_its_settings_name():
    agent = _load()

    assert (agent.family, agent.model) == ("claude", "claude-opus-5-5")


def test_an_agent_reads_the_skills_its_profile_names_from_the_app_folder(
    tmp_path: Path,
):
    profile = tmp_path / "profile.yaml"
    profile.write_text("skills: src/agents/job_analyst/skills\n")

    agent = _load(profile)

    assert agent.skills == _ROOT_PATH / "src/agents/job_analyst/skills"


def test_a_profile_reads_its_step_limit(tmp_path: Path):
    profile = tmp_path / "profile.yaml"
    profile.write_text("recursion_limit: 7\n")

    assert _load(profile).profile.recursion_limit == 7
    assert _load().profile.recursion_limit is None


def test_an_agent_reads_its_own_settings_with_its_profile_type(tmp_path: Path):
    profile = tmp_path / "profile.yaml"
    profile.write_text("recursion_limit: 7\ngreeting: Hi\n")

    agent = _load(profile, profile_type=GreeterProfile)

    assert agent.profile == GreeterProfile(recursion_limit=7, greeting="Hi")
    with pytest.raises(ValueError, match="greeting"):
        _load(profile)


def test_a_profile_that_names_no_skills_reads_them_beside_it():
    agent = _load()

    assert agent.system_prompt == PROFILE.parent / "prompts/system.md"
    assert agent.skills == PROFILE.parent / "skills"


def test_an_agent_reads_its_providers_prompt_variant_when_there_is_one(
    tmp_path: Path,
):
    shutil.copytree(PROFILE.parent, tmp_path, dirs_exist_ok=True)
    variant = tmp_path / "prompts/system.anthropic.md"
    variant.write_text((tmp_path / "prompts/system.md").read_text())

    assert _load(tmp_path / "profile.yaml", "claude").system_prompt == variant
    assert (
        _load(tmp_path / "profile.yaml", "glm").system_prompt
        == tmp_path / "prompts/system.md"
    )


def test_an_archived_provider_variant_is_skipped_for_the_default_prompt(
    tmp_path: Path,
):
    shutil.copytree(PROFILE.parent, tmp_path, dirs_exist_ok=True)
    default = tmp_path / "prompts/system.md"
    (tmp_path / "prompts/system.anthropic.md").write_text(
        default.read_text().replace('status: "active"', 'status: "archived"')
    )

    assert _load(tmp_path / "profile.yaml", "claude").system_prompt == default


def test_an_unknown_model_family_is_refused():
    with pytest.raises(ValueError, match="Input should be 'claude', 'glm' or 'openai'"):
        _load(family="gpt")
