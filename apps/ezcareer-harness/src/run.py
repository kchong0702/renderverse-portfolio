import argparse
import asyncio
import json
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

from openinference.instrumentation.langchain import LangChainInstrumentor
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic_core import to_jsonable_python

from src.features.import_document import ImportInput, import_task

Flow = Callable[[Path, object], Awaitable[object]]
"""Runs one flow on one task with the harness in a folder, returning its output"""

FLOWS: dict[str, Flow] = {
    "import": lambda harness, task: import_task(
        ImportInput.model_validate(task), harness
    ),
}
"""Every flow a probe can run, by name; each feature adds its own"""


def _trace(spans: Sequence[ReadableSpan]) -> dict:
    """The run's harness hashes, tool calls and check rounds, in the order they ran"""
    spans = sorted(spans, key=lambda span: span.start_time or 0)
    return {
        "harness_hashes": sorted(
            {
                hash_
                for span in spans
                if "metadata" in span.attributes
                and (
                    hash_ := json.loads(span.attributes["metadata"]).get("harness_hash")
                )
            }
        ),
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


async def run(flow: Flow, harness: Path, task: object) -> dict:
    """Runs a flow once and returns its output, or why it failed, with its trace"""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    instrumentor = LangChainInstrumentor()
    instrumentor.instrument(tracer_provider=provider)
    try:
        output, error = to_jsonable_python(await flow(harness, task)), None
    except Exception as failure:  # noqa: BLE001
        output, error = None, f"{type(failure).__name__}: {failure}"
    finally:
        instrumentor.uninstrument()
    return {
        "output": output,
        "error": error,
        "trace": _trace(exporter.get_finished_spans()),
    }


def main(argv: Sequence[str] | None = None) -> None:
    """Runs one flow on one task with a harness folder and writes the result as JSON"""
    parser = argparse.ArgumentParser(prog="python -m src.run")
    parser.add_argument("--flow", required=True, choices=sorted(FLOWS))
    parser.add_argument("--harness", required=True, type=Path)
    parser.add_argument(
        "--task", required=True, type=Path, help="the flow's input as JSON"
    )
    parser.add_argument(
        "--out", type=Path, help="where to write the result; stdout when left out"
    )
    args = parser.parse_args(argv)
    result = asyncio.run(
        run(FLOWS[args.flow], args.harness, json.loads(args.task.read_text()))
    )
    text = json.dumps(result, indent=2)
    if args.out:
        args.out.write_text(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
