import json
from pathlib import Path

import pytest
from langchain_core.messages import HumanMessage

from src import run
from src.agents import AgentConfig, build_agent
from src.infrastructure import get_tracer
from tests.agents.test_builder import FIXTURES, STAGE, _call
from tests.conftest import ScriptedChatModel


async def _greet(harness: Path, task: object) -> object:
    """A flow that greets the task's person and checks the greeting"""
    config = AgentConfig.load(harness, STAGE)
    model = ScriptedChatModel(
        replies=[
            _call("look_up_name", person=task["person"]),
            _call("Greeting", text="Hi, Ada!"),
        ]
    )
    result = await build_agent(config, model).ainvoke(
        {"messages": [HumanMessage(f"Greet {task['person']}")]}
    )
    greeting = result["structured_response"]
    with get_tracer(__name__).start_as_current_span("check") as span:
        span.set_attribute(
            "check.errors",
            json.dumps([e for check in config.checks for e in check(greeting)]),
        )
    if task["person"] == "nobody":
        raise ValueError("nobody to greet")
    return greeting


@pytest.fixture
def task(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setitem(run.FLOWS, "greet", _greet)
    path = tmp_path / "task.json"
    path.write_text(json.dumps({"person": "Lovelace"}))
    return path


def test_a_probe_writes_the_output_and_the_trace(task: Path, tmp_path: Path):
    out = tmp_path / "result.json"

    run.main(
        [
            "--flow",
            "greet",
            "--harness",
            str(FIXTURES),
            "--task",
            str(task),
            "--out",
            str(out),
        ]
    )

    result = json.loads(out.read_text())
    assert result["output"] == {"text": "Hi, Ada!"}
    assert result["error"] is None
    assert result["trace"]["harness_hashes"] == [AgentConfig.load(FIXTURES, STAGE).hash]
    [call] = result["trace"]["tool_calls"]
    assert call["name"] == "look_up_name"
    assert "Lovelace" in call["input"]
    assert result["trace"]["check_rounds"] == [["rude"]]


def test_a_failed_run_still_writes_its_trace(task: Path, tmp_path: Path, capsys):
    task.write_text(json.dumps({"person": "nobody"}))

    run.main(["--flow", "greet", "--harness", str(FIXTURES), "--task", str(task)])

    result = json.loads(capsys.readouterr().out)
    assert result["output"] is None
    assert result["error"] == "ValueError: nobody to greet"
    assert result["trace"]["check_rounds"] == [["rude"]]
