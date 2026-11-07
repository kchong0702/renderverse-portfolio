from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Any, Self

import yaml
from deepagents import DeepAgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, SkipValidation

Check = Callable[..., list[Any]]
"""A guardrail: a plain function that returns structured errors, empty when it passes"""


class HarnessFile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    name: str
    """Agent name, such as career-consultant"""

    model: str = Field(pattern=r"^[a-z_-]+:.+$")
    """provider:model, such as anthropic:claude-sonnet-5-5"""

    tools: list[str] = Field(default_factory=list)
    """Stage tools the agent gets, each described by tools/<name>.md"""

    middleware: list[str] = Field(default_factory=list)
    """Stage middleware the agent runs"""

    checks: list[str] = Field(default_factory=list)
    """Stage checks the flow runs on the agent's answer"""

    response_format: str
    """Name of the model the agent answers with"""

    recursion_limit: int = Field(gt=0)
    """Graph steps an agent run may take before it fails"""


@dataclass(frozen=True)
class Stage:
    tools: Mapping[str, BaseTool]
    """Every tool a harness of this stage may pick, by name"""

    response_formats: Mapping[str, type[BaseModel]]
    """Every answer model a harness may pick, by name"""

    checks: Mapping[str, Check] = field(default_factory=dict)
    """Every check a harness may turn on, by name"""

    middleware: Mapping[str, AgentMiddleware] = field(default_factory=dict)
    """Every middleware a harness may pick, by name"""

    state_schema: type[DeepAgentState] = DeepAgentState
    """The agent's state, which the stage's tools read"""

    context_schema: type | None = None
    """What a run passes as context, which the stage's tools read"""


def _pick[T](kind: str, names: list[str], available: Mapping[str, T]) -> tuple[T, ...]:
    """The named items, refusing a name the stage doesn't offer"""
    if unknown := [name for name in names if name not in available]:
        raise ValueError(
            f"unknown {kind} {unknown}; the stage offers {sorted(available)}"
        )
    return tuple(available[name] for name in names)


class AgentConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        use_attribute_docstrings=True,
    )

    folder: Path
    """The harness folder: system.md, harness.yaml, tools/ and skills/"""

    name: str
    """Agent name, such as career-consultant"""

    model: str
    """provider:model, such as anthropic:claude-sonnet-5-5"""

    tools: tuple[BaseTool, ...] = ()
    """Tools the stage adds to the read-only file tools, described by tools/<name>.md"""

    middleware: tuple[AgentMiddleware, ...] = ()
    """Middleware the stage adds to the deep agent's own"""

    checks: tuple[Check, ...] = ()
    """Checks the flow runs on the agent's answer"""

    response_format: type[BaseModel]
    """What the agent answers with"""

    state_schema: Annotated[type[DeepAgentState], SkipValidation] = DeepAgentState
    """The agent's state, which the stage's tools read"""

    context_schema: type | None = None
    """What a run passes as context, which the stage's tools read"""

    recursion_limit: int = Field(gt=0)
    """Graph steps an agent run may take before it fails"""

    @property
    def system_prompt(self) -> Path:
        """The harness's system.md"""
        return self.folder / "system.md"

    @property
    def skills(self) -> Path:
        """The harness's skills folder, holding one SKILL.md folder per skill"""
        return self.folder / "skills"

    @property
    def hash(self) -> str:
        """Sha256 of every file in the harness folder, with its path"""
        digest = sha256()
        for path in sorted(self.folder.rglob("*")):
            if path.is_file():
                digest.update(str(path.relative_to(self.folder)).encode() + b"\0")
                digest.update(path.read_bytes() + b"\0")
        return digest.hexdigest()

    @classmethod
    def load(cls, folder: Path, stage: Stage) -> Self:
        """Reads a harness folder, picking its tools, middleware, checks and
        answer model by name from what the stage offers"""
        harness = HarnessFile.model_validate(
            yaml.safe_load((folder / "harness.yaml").read_text())
        )
        return cls(
            folder=folder,
            name=harness.name,
            model=harness.model,
            tools=tuple(
                tool.model_copy(
                    update={
                        "description": (folder / "tools" / f"{tool.name}.md")
                        .read_text()
                        .strip()
                    }
                )
                for tool in _pick("tools", harness.tools, stage.tools)
            ),
            middleware=_pick("middleware", harness.middleware, stage.middleware),
            checks=_pick("checks", harness.checks, stage.checks),
            response_format=_pick(
                "response format", [harness.response_format], stage.response_formats
            )[0],
            state_schema=stage.state_schema,
            context_schema=stage.context_schema,
            recursion_limit=harness.recursion_limit,
        )
