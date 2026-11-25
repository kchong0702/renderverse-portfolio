from collections.abc import Mapping
from hashlib import sha256
from pathlib import Path
from typing import Self

import yaml
from deepagents import HarnessProfileConfig, register_harness_profile
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.agents.prompt import is_active
from src.clients.llm_providers import PROVIDERS
from src.core.config import _ROOT_PATH, AgentSettings, Family, get_settings


class AgentProfile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    skills: Path | None = None
    """The agent's skills folder, from the app folder; None reads skills/ beside profile.yaml"""

    tool_description_overrides: dict[str, str] = Field(default_factory=dict)
    """Descriptions that replace a tool's own, by tool name"""

    recursion_limit: int | None = Field(default=None, gt=0)
    """Most steps one turn of the agent may take when served on its own; None keeps
    LangGraph's default"""

    @field_validator("skills")
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
    """Holds profile.yaml, prompts/ and the agent's own skills/"""

    family: Family
    """Model family the model belongs to, such as glm"""

    model: str
    """Exact model the agent runs on, such as glm-5.3"""

    profile: AgentProfile
    """The agent's own settings, from its profile.yaml"""

    @property
    def system_prompt(self) -> Path:
        """The agent's system prompt file: prompts/system.<provider>.md when there is
        an active one for its provider, else prompts/system.md"""
        variant = self.folder / "prompts" / f"system.{self.provider}.md"
        if variant.is_file() and is_active(variant):
            return variant
        return self.folder / "prompts" / "system.md"

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
        """Sha256 of every file in the agent's folder and in the middleware prompts
        folder, each with its path from that folder"""
        digest = sha256()
        for folder in (self.folder, get_settings().middleware_prompts):
            for path in sorted(folder.rglob("*")):
                if path.is_file():
                    digest.update(str(path.relative_to(folder)).encode() + b"\0")
                    digest.update(path.read_bytes() + b"\0")
        return digest.hexdigest()

    @classmethod
    def load(
        cls, settings: AgentSettings, profile_type: type[AgentProfile] = AgentProfile
    ) -> Self:
        """Reads an agent's profile.yaml as profile_type, for the model and family its
        settings name"""
        return cls(
            name=settings.name,
            folder=settings.path.parent,
            family=settings.family,
            model=settings.model,
            profile=profile_type.model_validate(
                yaml.safe_load(settings.path.read_text())
            ),
        )


def load_agents(
    agents: tuple[AgentSettings, ...],
    profiles: Mapping[str, type[AgentProfile]] = {},
) -> dict[str, Agent]:
    """Every agent the settings list, by name, each profile read as its type in
    profiles, else as AgentProfile"""
    return {
        settings.name: Agent.load(settings, profiles.get(settings.name, AgentProfile))
        for settings in agents
    }


def register_harness_profiles(path: Path) -> None:
    """Registers each model's harness profile in path, by provider or
    provider:model; the app does it once at startup, before building any agent"""
    for key, profile in yaml.safe_load(path.read_text()).items():
        register_harness_profile(key, HarnessProfileConfig.from_dict(profile))
