import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from scripts import probe
from src.agents import build_agent, load_agents
from src.core.config import get_settings, reload_settings
from src.infrastructure import get_tracer
from tests.agents.test_builder import FIXTURES, Greeting, _call, look_up_name
from tests.conftest import ScriptedChatModel


class GreetProfile(BaseModel):
    checks: list[str]
    recursion_limit: int


CHECKS = {"polite": lambda greeting: [] if "Hello" in greeting.text else ["rude"]}


async def _greet(task: object) -> object:
    """A workflow that greets the task's person with its harness and checks the greeting"""
    settings = get_settings()
    profile = settings.graph_profile("greet").load(GreetProfile)
    model = ScriptedChatModel(
        replies=[
            _call("look_up_name", person=task["person"]),
            _call("Greeting", text="Hi, Ada!"),
        ]
    )
    agent = build_agent(
        load_agents(settings.agents)["greeter"],
        response_format=Greeting,
        tools=(look_up_name,),
        model=model,
    )
    result = await agent.ainvoke(
        {"messages": [HumanMessage(f"Greet {task['person']}")]},
        {"recursion_limit": profile.recursion_limit},
    )
    greeting = result["structured_response"]
    with get_tracer(__name__).start_as_current_span("checks") as span:
        span.set_attribute(
            "check.errors",
            json.dumps([e for name in profile.checks for e in CHECKS[name](greeting)]),
        )
    if task["person"] == "nobody":
        raise ValueError("nobody to greet")
    return greeting


def _candidate(folder: Path) -> Path:
    """A candidate harness: copies of the greeter and the greet graph's folder,
    and a config.toml that names them"""
    shutil.copytree(FIXTURES / "greeter", folder / "greeter")
    shutil.copytree(Path(__file__).parent / "fixtures/greet", folder / "greet")
    config = folder / "config.toml"
    config.write_text(
        f'[[agents]]\nname = "greeter"\npath = "{folder}/greeter/profile.yaml"\n'
        'model = "glm-5.3"\n\n'
        f'[[graph_profiles]]\nname = "greet"\npath = "{folder}/greet/profile.yaml"\n'
    )
    return config


@pytest.fixture
def task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setitem(probe.WORKFLOWS, "greet", _greet)
    monkeypatch.delenv("EZCAREER_HARNESS_CONFIG", raising=False)
    path = tmp_path / "task.json"
    path.write_text(json.dumps({"person": "Lovelace"}))
    yield path
    monkeypatch.delenv("EZCAREER_HARNESS_CONFIG", raising=False)
    reload_settings()


def test_a_probe_runs_a_candidate_and_writes_its_output_and_trace(
    task: Path, tmp_path: Path
):
    config = _candidate(tmp_path / "candidate")
    out = tmp_path / "result.json"

    probe.main(
        [
            "--workflow",
            "greet",
            "--task",
            str(task),
            "--config",
            str(config),
            "--out",
            str(out),
        ]
    )

    result = json.loads(out.read_text())
    assert result["output"] == {"text": "Hi, Ada!"}
    assert result["error"] is None
    assert result["harness_hash"] == probe.harness_hash(get_settings())
    [call] = result["trace"]["tool_calls"]
    assert call["name"] == "look_up_name"
    assert "Lovelace" in call["input"]
    assert result["trace"]["check_rounds"] == [["rude"]]


def test_editing_any_harness_file_changes_the_harness_hash(task: Path, tmp_path: Path):
    config = _candidate(tmp_path / "candidate")
    probe.main(["--workflow", "greet", "--task", str(task), "--config", str(config)])
    before = probe.harness_hash(get_settings())

    for changed in (
        "greeter/system.md",
        "greeter/profile.yaml",
        "greet/profile.yaml",
        "greet/prompt.md",
    ):
        path = tmp_path / "candidate" / changed
        path.write_text(path.read_text() + "\n")
        assert probe.harness_hash(reload_settings()) != before


def test_a_failed_run_still_writes_its_trace(task: Path, tmp_path: Path, capsys):
    config = _candidate(tmp_path / "candidate")
    task.write_text(json.dumps({"person": "nobody"}))

    probe.main(["--workflow", "greet", "--task", str(task), "--config", str(config)])

    result = json.loads(capsys.readouterr().out)
    assert result["output"] is None
    assert result["error"] == "ValueError: nobody to greet"
    assert result["trace"]["check_rounds"] == [["rude"]]
