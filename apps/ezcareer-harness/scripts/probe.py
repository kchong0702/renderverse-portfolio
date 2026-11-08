import argparse
import asyncio
import json
import os
from collections.abc import Awaitable, Callable, Sequence
from hashlib import sha256
from pathlib import Path

from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic_core import to_jsonable_python

from src.app.container import Container
from src.core.config import Settings, reload_settings

RunWorkflow = Callable[[object], Awaitable[object]]
"""Runs one workflow on one task, returning its output"""

WORKFLOWS: dict[str, RunWorkflow] = {
    "analyse-job": lambda task: (
        Container()
        .analyse_job_graph()
        .ainvoke(task, {"configurable": {"thread_id": "probe"}})
    ),
    "find-jobs": lambda task: (
        Container()
        .find_jobs_graph()
        .ainvoke(task, {"configurable": {"thread_id": "probe"}})
    ),
}
"""Every workflow a probe can run, by name"""


def harness_hash(settings: Settings) -> str:
    """Sha256 of the harness the settings name: every file of every agent folder
    and every graph's harness folder, with its path"""
    paths = [agent.path.parent for agent in settings.agents]
    paths += [profile.folder for profile in settings.graph_profiles]
    digest = sha256()
    for root in paths:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                digest.update(str(path).encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def _trace(spans: Sequence[ReadableSpan]) -> dict:
    """The run's tool calls and check rounds, in the order they ran"""
    spans = sorted(spans, key=lambda span: span.start_time or 0)
    return {
        "tool_calls": [
            {
                "name": span.name,
                "input": span.attributes.get("input.value"),
                "output": span.attributes.get("output.value"),
            }
            for span in spans
            if span.attributes.get("openinference.span.kind") == "TOOL"
        ],
        "check_rounds": [
            json.loads(span.attributes["check.errors"])
            for span in spans
            if "check.errors" in span.attributes
        ],
    }


async def probe(workflow: RunWorkflow, task: object) -> dict:
    """Runs a workflow once with the current settings and returns its output, or
    why it failed, with the harness hash and the trace"""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    instrumentor = LangChainInstrumentor()
    instrumentor.instrument(tracer_provider=provider)
    try:
        output, error = to_jsonable_python(await workflow(task)), None
    except Exception as failure:  # noqa: BLE001
        output, error = None, f"{type(failure).__name__}: {failure}"
    finally:
        instrumentor.uninstrument()
    return {
        "harness_hash": harness_hash(reload_settings()),
        "output": output,
        "error": error,
        "trace": _trace(exporter.get_finished_spans()),
    }


def main(argv: Sequence[str] | None = None) -> None:
    """Runs one workflow on one task with a candidate harness and writes the result
    as JSON"""
    parser = argparse.ArgumentParser(prog="python -m scripts.probe")
    parser.add_argument("--workflow", required=True, choices=sorted(WORKFLOWS))
    parser.add_argument(
        "--task", required=True, type=Path, help="the workflow's input as JSON"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="a candidate config.toml; the app's own when left out",
    )
    parser.add_argument(
        "--out", type=Path, help="where to write the result; stdout when left out"
    )
    args = parser.parse_args(argv)
    if args.config:
        os.environ["EZCAREER_HARNESS_CONFIG"] = str(args.config.resolve())
    reload_settings()
    result = asyncio.run(
        probe(WORKFLOWS[args.workflow], json.loads(args.task.read_text()))
    )
    text = json.dumps(result, indent=2)
    if args.out:
        args.out.write_text(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
