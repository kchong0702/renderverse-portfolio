import json

from langchain_core.messages import AIMessage, ToolMessage

from tests.agents.career_director.test_handoffs import _graph, _turn
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel

STARTED = {
    "started": [
        {"document_id": "doc-1", "title": "Backend résumé"},
        {"document_id": "doc-2", "title": "Platform résumé"},
    ],
    "skipped": [{"document_id": "doc-3", "reason": "A change waits for review"}],
}


def _report(result: dict, tool: str) -> ToolMessage:
    """The one result the tool returned this turn"""
    [report] = [
        m for m in result["messages"] if isinstance(m, ToolMessage) and m.name == tool
    ]
    return report


async def test_edits_to_several_documents_start_through_ops_api_and_return_at_once():
    director = ScriptedChatModel(
        replies=[
            _call(
                "edit_documents",
                document_ids=["doc-1", "doc-2", "doc-3"],
                instruction="Mention Kubernetes",
            ),
            AIMessage("I started on two résumés."),
        ]
    )

    asked, result = await _turn(
        _graph(director, ScriptedChatModel(replies=[])),
        "Mention Kubernetes in all my résumés",
        STARTED,
    )

    assert asked == [
        {
            "execute_tool": "edit_documents",
            "document_ids": ["doc-1", "doc-2", "doc-3"],
            "instruction": "Mention Kubernetes",
        }
    ]
    report = _report(result, "edit_documents")
    assert json.loads(report.text) == STARTED
    assert report.artifact == {"step_detail": "2 documents"}
    assert result["messages"][-1].text == "I started on two résumés."


async def test_tailoring_for_a_saved_job_starts_through_ops_api():
    director = ScriptedChatModel(
        replies=[
            _call("tailor_documents", job_id="job-kopi"),
            AIMessage("I started tailoring a copy of your résumé."),
        ]
    )
    started = {"started": STARTED["started"][:1], "skipped": []}

    asked, result = await _turn(
        _graph(director, ScriptedChatModel(replies=[])),
        "Tailor my résumé and letter for the Kopi job",
        started,
    )

    assert asked == [{"execute_tool": "tailor_documents", "job_id": "job-kopi"}]
    report = _report(result, "tailor_documents")
    assert json.loads(report.text) == started
    assert report.artifact == {"step_detail": "1 document"}


async def test_work_ops_api_refuses_tells_the_director_nothing_started():
    director = ScriptedChatModel(
        replies=[
            _call("tailor_documents", job_id="job-gone"),
            AIMessage("That job is gone."),
        ]
    )

    _, result = await _turn(
        _graph(director, ScriptedChatModel(replies=[])),
        "Tailor my résumé for that job",
        {"error": "No job job-gone"},
    )

    report = _report(result, "tailor_documents")
    assert report.text == "No tailoring started: No job job-gone"
    assert report.artifact == {}
