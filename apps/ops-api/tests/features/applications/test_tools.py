from tests.conftest import (
    PREFIX,
    ask,
    sent_messages,
    sse_events,
    tool_pause,
)

APPLICATIONS = f"{PREFIX}/applications"
STAGES = ["draft", "applied", "replied", "interview", "offer", "closed"]


async def _answer(client, harness, request: dict) -> dict:
    """What ops-api resumed career-director with after it paused on this tool"""
    response = await ask(
        client,
        harness,
        "How many applications do I have?",
        *tool_pause(request, "Found them."),
    )
    assert sse_events(response)[-1] == {"status": "completed", "reply": "Found them."}
    return sent_messages(harness)[-1]["message"]["parts"][0]["data"]


async def _apply(client, company: str, stage: str) -> dict:
    """Track an application added by hand"""
    response = await client.post(
        APPLICATIONS, json={"company": company, "role": "Engineer", "stage": stage}
    )
    return response.json()


async def test_applications_are_counted_by_stage_and_listed_with_their_next_step(
    client, harness
):
    harbor = await _apply(client, "Harbor Health", "interview")
    await client.post(
        f"{APPLICATIONS}/{harbor['id']}/steps",
        json={"kind": "take_home", "title": "Coding task", "due_on": "2099-01-05"},
    )
    await _apply(client, "Kopi Cloud", "applied")
    await _apply(client, "Lumen Pay", "applied")

    answer = await _answer(client, harness, {"execute_tool": "applications"})

    assert answer["by_stage"] == dict.fromkeys(STAGES, 0) | {
        "applied": 2,
        "interview": 1,
    }
    assert answer["timezone"] == "UTC"
    assert [a["company"] for a in answer["applications"]] == [
        "Harbor Health",
        "Lumen Pay",
        "Kopi Cloud",
    ]
    assert answer["applications"][0] == {
        "company": "Harbor Health",
        "role": "Engineer",
        "stage": "interview",
        "applied_on": None,
        "fit": None,
        "next_step": {
            "kind": "take_home",
            "title": "Coding task",
            "starts_at": None,
            "due_on": "2099-01-05",
            "format": None,
            "location": None,
        },
        "overdue": [],
    }


async def test_a_company_narrows_the_counts_and_a_stage_only_the_list(client, harness):
    await _apply(client, "Harbor Health", "applied")
    await _apply(client, "Harbor Labs", "offer")
    await _apply(client, "Kopi Cloud", "applied")

    answer = await _answer(
        client,
        harness,
        {"execute_tool": "applications", "company": "HARBOR", "stage": "applied"},
    )

    assert answer["by_stage"] == dict.fromkeys(STAGES, 0) | {"applied": 1, "offer": 1}
    assert [a["company"] for a in answer["applications"]] == ["Harbor Health"]
