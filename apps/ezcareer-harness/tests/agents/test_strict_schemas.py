import pytest
from document_schema import Changeset
from langchain.agents.structured_output import ProviderStrategy
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from src.clients.llm_providers import llm_provider
from src.features.analyse_job import JobRequirements
from src.features.find_jobs import RankedJobs
from src.features.import_document import ResumeImport


def _empty_objects(node: object, at: str) -> list[str]:
    """Where a schema has an object with no properties, which strict output
    can only fill with {}"""
    match node:
        case {"type": "object"} if not node.get("properties"):
            return [at]
        case dict():
            return [
                path
                for key, child in node.items()
                for path in _empty_objects(child, f"{at}/{key}")
            ]
        case list():
            return [
                path
                for index, child in enumerate(node)
                for path in _empty_objects(child, f"{at}/{index}")
            ]
    return []


@pytest.mark.parametrize(
    "response_format", [Changeset, ResumeImport, JobRequirements, RankedJobs]
)
def test_claude_strict_output_takes_every_response_format_with_closed_shapes(
    response_format: type[BaseModel], monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")

    payload = llm_provider("claude", "claude-opus-5-5")._get_request_payload(
        [HumanMessage("Hi")],
        **ProviderStrategy(schema=response_format).to_model_kwargs(),
    )

    assert _empty_objects(payload["output_config"]["format"]["schema"], "#") == []
