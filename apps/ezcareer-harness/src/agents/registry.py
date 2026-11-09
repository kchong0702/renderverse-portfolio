from functools import cache
from hashlib import sha256
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field

from src.clients.llm_providers import PROVIDERS
from src.core.config import AgentSettings


class AgentProfile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    system_prompt: Path = Path("system.md")
    """The agent's system prompt, relative to its folder"""

    skills: Path = Path("skills")
    """The agent's skills folder, one SKILL.md folder per skill, relative to its folder"""

    models: dict[str, list[str]]
    """Models the agent can run on, by family, such as glm"""

    excluded_tools: frozenset[str] = frozenset()
    """Tools the agent is never offered, such as deepagents' write_file"""

    tool_description_overrides: dict[str, str] = Field(default_factory=dict)
    """Descriptions that replace a tool's own, by tool name"""


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

    family: str
    """Model family profile.yaml lists the model under, such as glm"""

    model: str
    """Exact model the agent runs on, such as glm-5.3"""

    profile: AgentProfile
    """The agent's own settings, from its profile.yaml"""

    @property
    def system_prompt(self) -> Path:
        """The agent's system prompt file"""
        return self.folder / self.profile.system_prompt

    @property
    def skills(self) -> Path:
        """The agent's skills folder"""
        return self.folder / self.profile.skills

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
        """Reads an agent's profile.yaml and checks it lists the model it runs on
        under exactly one known family"""
        profile = AgentProfile.model_validate(yaml.safe_load(settings.path.read_text()))
        families = [
            family
            for family, models in profile.models.items()
            if settings.model in models
        ]
        if len(families) != 1:
            raise ValueError(
                f"{settings.path} must list {settings.model} under exactly one family"
            )
        if families[0] not in PROVIDERS:
            raise ValueError(f"{settings.path}: unknown model family {families[0]}")
        return cls(
            name=settings.name,
            folder=settings.path.parent,
            family=families[0],
            model=settings.model,
            profile=profile,
        )


@cache
def load_agents(agents: tuple[AgentSettings, ...]) -> dict[str, Agent]:
    """Every agent the settings list, by name, read once per list"""
    return {settings.name: Agent.load(settings) for settings in agents}
