from functools import cache
from hashlib import sha256
from pathlib import Path
from typing import Self

import yaml
from deepagents import HarnessProfileConfig
from pydantic import BaseModel, ConfigDict

from src.core.config import AgentSettings
from src.shared.clients.chat_models import PROVIDERS


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
    """Model family the model belongs to in profile.yaml, such as glm"""

    model: str
    """Exact model the agent runs on, such as glm-5.3"""

    profile: HarnessProfileConfig
    """The deepagents harness profile profile.yaml gives that model"""

    @property
    def system_prompt(self) -> Path:
        """The agent's system.md"""
        return self.folder / "system.md"

    @property
    def skills(self) -> Path:
        """The agent's skills folder, holding one SKILL.md folder per skill"""
        return self.folder / "skills"

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
        """Reads an agent's profile.yaml, whose profiles are grouped by family and
        then exact model, and picks the profile of the model it runs on"""
        families: dict[str, dict[str, dict]] = yaml.safe_load(settings.path.read_text())
        found = [
            (family, models[settings.model])
            for family, models in families.items()
            if settings.model in models
        ]
        if len(found) != 1:
            raise ValueError(
                f"{settings.path} needs exactly one profile for {settings.model}"
            )
        [(family, profile)] = found
        if family not in PROVIDERS:
            raise ValueError(f"{settings.path}: unknown model family {family}")
        return cls(
            name=settings.name,
            folder=settings.path.parent,
            family=family,
            model=settings.model,
            profile=HarnessProfileConfig.from_dict(profile),
        )


@cache
def load_agents(agents: tuple[AgentSettings, ...]) -> dict[str, Agent]:
    """Every agent the settings list, by name, read once per list"""
    return {settings.name: Agent.load(settings) for settings in agents}
