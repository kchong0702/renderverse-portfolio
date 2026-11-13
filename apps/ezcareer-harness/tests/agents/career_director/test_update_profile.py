from langchain_core.messages import AIMessage, ToolMessage

from tests.agents.career_director.test_handoffs import _graph, _turn
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel

READ_SKILL = _call("read_file", file_path="/update-profile/SKILL.md")
HEADLINE = {"kind": "about", "field": "headline", "value": "Staff backend engineer"}
SKILL = {"kind": "new_skill", "name": "Kubernetes", "group": ""}
UPDATE = _call("update_profile", edits=[HEADLINE, SKILL], source="Backend résumé")
REVIEW = {
    "action_requests": [
        {
            "name": "update_profile",
            "args": {"edits": [HEADLINE, SKILL], "source": "Backend résumé"},
        }
    ],
    "review_configs": [
        {"action_name": "update_profile", "allowed_decisions": ["approve", "reject"]}
    ],
}


def _review(asked: dict) -> dict:
    """An approval request as paused, without its generated description"""
    return asked | {
        "action_requests": [
            {k: v for k, v in request.items() if k != "description"}
            for request in asked["action_requests"]
        ]
    }


def _reports(result: dict, tool: str) -> list[ToolMessage]:
    return [
        m for m in result["messages"] if isinstance(m, ToolMessage) and m.name == tool
    ]


async def test_a_synced_document_is_saved_only_after_the_user_approves():
    director = ScriptedChatModel(
        replies=[
            READ_SKILL,
            _call("preview_profile_sync", document_id="doc-1"),
            UPDATE,
            AIMessage("I saved your headline and Kubernetes."),
        ]
    )

    asked, result = await _turn(
        _graph(director, ScriptedChatModel(replies=[])),
        "Sync my details with my Backend résumé",
        {"edits": [HEADLINE, SKILL]},
        {"decisions": [{"type": "approve"}]},
        {"saved": 2},
    )

    syncing, reviewing, saving = asked
    assert syncing == {"execute_tool": "profile_sync", "document_id": "doc-1"}
    assert _review(reviewing) == REVIEW
    assert saving == {"execute_tool": "profile_update", "edits": [HEADLINE, SKILL]}
    assert "update_profile" not in director.offered_tools[0]
    assert {"preview_profile_sync", "update_profile"} <= director.offered_tools[1]
    [preview] = _reports(result, "preview_profile_sync")
    assert preview.artifact == {"step_detail": "2 changes"}
    [report] = _reports(result, "update_profile")
    assert report.text == "Saved 2 changes to the user's profile."
    assert report.artifact == {
        "name": "profile_updated",
        "data": {"saved": 2},
        "step_detail": "2 changes",
    }
    assert result["messages"][-1].text == "I saved your headline and Kubernetes."


async def test_a_rejected_update_is_never_saved_and_the_director_hears_why():
    director = ScriptedChatModel(
        replies=[READ_SKILL, UPDATE, AIMessage("I left your headline as it was.")]
    )

    asked, result = await _turn(
        _graph(director, ScriptedChatModel(replies=[])),
        "Change my headline to Staff backend engineer",
        {"decisions": [{"type": "reject", "message": "Keep my old headline"}]},
    )

    [reviewing] = asked
    assert _review(reviewing) == REVIEW
    assert "__interrupt__" not in result
    [rejected] = [
        m
        for m in director.requests[-1]
        if isinstance(m, ToolMessage) and m.name == "update_profile"
    ]
    assert rejected.status == "error"
    assert "Keep my old headline" in rejected.text
    assert result["messages"][-1].text == "I left your headline as it was."


async def test_a_save_ops_api_refuses_tells_the_director_nothing_was_saved():
    director = ScriptedChatModel(
        replies=[READ_SKILL, UPDATE, AIMessage("Nothing was saved.")]
    )

    _, result = await _turn(
        _graph(director, ScriptedChatModel(replies=[])),
        "Change my headline to Staff backend engineer",
        {"decisions": [{"type": "approve"}]},
        {"error": "No such entry role-9"},
    )

    [report] = _reports(result, "update_profile")
    assert report.text == "Nothing was saved: No such entry role-9"
    assert report.artifact == {}
