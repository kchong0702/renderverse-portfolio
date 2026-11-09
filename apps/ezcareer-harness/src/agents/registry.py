from functools import cache
from hashlib import sha256
from pathlib import Path
from typing import Self

import yaml
from deepagents import HarnessProfileConfig, register_harness_profile
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.clients.llm_providers import PROVIDERS
from src.core.config import _ROOT_PATH, AgentSettings, Family


class AgentProfile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    system_prompt: Path | None = None
    """The agent's system prompt, from the app folder; None reads system.md beside profile.yaml"""

    skills: Path | None = None
    """The agent's skills folder, from the app folder; None reads skills/ beside profile.yaml"""

    tool_description_overrides: dict[str, str] = Field(default_factory=dict)
    """Descriptions that replace a tool's own, by tool name"""

    @field_validator("system_prompt", "skills")
    @classmethod
    def _from_app_folder(cls, path: Path | None) -> Path | None:
        """Reads a relative path from the app folder"""
        return path if path is None or path.is_absolute() else _ROOT_PATH / path


class Agent(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        use_attribute_docstrings=True,
    )

    name: str
    """Agent name, such as career-consultant"""

    folder: Path
    """Holds profile.yaml, system.md and the agent's own skills/"""

    family: Family
    """Model family the model belongs to, such as glm"""

    model: str
    """Exact model the agent runs on, such as glm-5.3"""

    profile: AgentProfile
    """The agent's own settings, from its profile.yaml"""

    @property
    def system_prompt(self) -> Path:
        """The agent's system prompt file"""
        return self.profile.system_prompt or self.folder / "system.md"

    @property
    def skills(self) -> Path:
        """The agent's skills folder"""
        return self.profile.skills or self.folder / "skills"

    @property
    def provider(self) -> str:
        """The LangChain provider the model runs on, which deepagents keys profiles by"""
        return PROVIDERS[self.family]

    @property
    def hash(self) -> str:
        """Sha256 of every file in the agent's folder, with its path"""
        digest = sha256()
        for path in sorted(self.folder.rglob("*")):
            if path.is_file():
                digest.update(str(path.relative_to(self.folder)).encode() + b"\0")
                digest.update(path.read_bytes() + b"\0")
        return digest.hexdigest()

    @classmethod
    def load(cls, settings: AgentSettings) -> Self:
        """Reads an agent's profile.yaml for the model and family its settings name"""
        return cls(
            name=settings.name,
            folder=settings.path.parent,
            family=settings.family,
            model=settings.model,
            profile=AgentProfile.model_validate(
                yaml.safe_load(settings.path.read_text())
            ),
        )


@cache
def load_agents(agents: tuple[AgentSettings, ...]) -> dict[str, Agent]:
    """Every agent the settings list, by name, read once per list"""
    return {settings.name: Agent.load(settings) for settings in agents}


def register_harness_profiles(path: Path) -> None:
    """Registers each model's harness profile in path, by provider or
    provider:model; the app does it once at startup, before building any agent"""
    for key, profile in yaml.safe_load(path.read_text()).items():
        register_harness_profile(key, HarnessProfileConfig.from_dict(profile))
