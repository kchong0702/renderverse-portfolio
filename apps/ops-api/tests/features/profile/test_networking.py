from tests.conftest import PREFIX, a2a_sent, a2a_task

PROFILE = f"{PREFIX}/profile"

AIM = "Senior backend roles in fintech"


def _written(reply: dict) -> dict:
    """write-networking's reply"""
    return a2a_task("COMPLETED", artifact_parts=[{"data": reply}])


async def _role(client, title: str, archived: bool) -> str:
    """Add a role and return its fact id"""
    entry = await client.post(
        f"{PROFILE}/entries",
        json={
            "kind": "role",
            "title": title,
            "organisation": "Acme",
            "archived": archived,
        },
    )
    return f"role-{entry.json()['id']}"


async def test_networking_starts_empty(client):
    response = await client.get(f"{PROFILE}/networking")

    assert response.json() == {
        "aim": "",
        "headline": None,
        "summary": None,
        "descriptions": [],
    }


async def test_the_copy_is_written_from_every_fact_and_kept(client, harness):
    await client.patch(PROFILE, json={"headline": "Backend engineer"})
    used = await _role(client, "Senior Engineer", archived=False)
    archived = await _role(client, "Engineer", archived=True)
    copy = {
        "headline": {"text": "Backend engineer for payments", "facts": [used]},
        "summary": {"text": "I build payment systems.", "facts": [used, archived]},
        "descriptions": [
            {"fact": used, "text": "Led payments.", "facts": [used]},
            {"fact": archived, "text": "Built ledgers.", "facts": [archived]},
        ],
    }
    harness.outcomes = [_written(copy)]

    written = await client.post(f"{PROFILE}/networking", json={"aim": AIM})

    assert written.status_code == 200
    assert written.json() == {"aim": AIM, **copy}
    assert (await client.get(f"{PROFILE}/networking")).json() == written.json()
    [request] = harness.received
    assert request.url.path == "/ezcareer/a2a/write-networking"
    data = a2a_sent(harness)[0]["params"]["message"]["parts"][0]["data"]
    assert data["aim"] == AIM
    assert data["only"] is None
    assert {fact["id"] for fact in data["facts"]} == {"about", used, archived}


async def test_one_part_is_rewritten_alone(client, harness):
    used = await _role(client, "Senior Engineer", archived=False)
    harness.outcomes = [
        _written(
            {
                "headline": {"text": "Backend engineer", "facts": [used]},
                "summary": {"text": "I build things.", "facts": [used]},
                "descriptions": [{"fact": used, "text": "Led it.", "facts": [used]}],
            }
        ),
        _written({"headline": {"text": "Payments engineer", "facts": [used]}}),
        _written(
            {"descriptions": [{"fact": used, "text": "Led payments.", "facts": [used]}]}
        ),
    ]
    await client.post(f"{PROFILE}/networking", json={"aim": AIM})

    await client.post(f"{PROFILE}/networking", json={"aim": AIM, "only": "headline"})
    rewritten = await client.post(
        f"{PROFILE}/networking", json={"aim": "Payments roles", "only": used}
    )

    assert rewritten.json() == {
        "aim": "Payments roles",
        "headline": {"text": "Payments engineer", "facts": [used]},
        "summary": {"text": "I build things.", "facts": [used]},
        "descriptions": [{"fact": used, "text": "Led payments.", "facts": [used]}],
    }
    assert [
        sent["params"]["message"]["parts"][0]["data"]["only"]
        for sent in a2a_sent(harness)
    ] == [
        None,
        "headline",
        used,
    ]


async def test_rewriting_a_fact_that_is_gone_is_not_found(client, harness):
    response = await client.post(
        f"{PROFILE}/networking", json={"aim": AIM, "only": "role-gone"}
    )

    assert response.status_code == 404
    assert harness.received == []
