from tests.conftest import PREFIX


async def test_models_come_from_the_harness(client, harness):
    response = await client.get(f"{PREFIX}/settings/models")

    assert response.status_code == 200
    assert response.json() == harness.catalog


async def test_patch_saves_a_model_the_harness_offers(client):
    choice = {"family": "openai", "model": "gpt-5-mini"}

    response = await client.patch(f"{PREFIX}/settings", json={"ai_model": choice})

    assert response.status_code == 200
    assert response.json()["ai_model"] == choice
    reread = await client.get(f"{PREFIX}/settings")
    assert reread.json()["ai_model"] == choice


async def test_patch_rejects_a_model_the_harness_does_not_offer(client):
    response = await client.patch(
        f"{PREFIX}/settings",
        json={
            "job_agent": {"min_score": 90},
            "ai_model": {"family": "claude", "model": "gpt-5"},
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "ezcareer-harness does not offer gpt-5 for claude"
    )
    reread = await client.get(f"{PREFIX}/settings")
    assert reread.json()["ai_model"] is None
    assert reread.json()["job_agent"]["min_score"] == 70


async def test_patch_rejects_an_unknown_family(client):
    response = await client.patch(
        f"{PREFIX}/settings", json={"ai_model": {"family": "gemini", "model": "x"}}
    )

    assert response.status_code == 422


async def test_unreachable_harness_gives_a_clear_error(client, harness):
    harness.down = True
    unavailable = "ezcareer-harness did not return its models; try again later"

    models = await client.get(f"{PREFIX}/settings/models")
    patch = await client.patch(
        f"{PREFIX}/settings",
        json={"ai_model": {"family": "claude", "model": "claude-sonnet-4-5"}},
    )

    assert models.status_code == 503
    assert models.json() == {"detail": unavailable}
    assert patch.status_code == 503
    assert patch.json() == {"detail": unavailable}


async def test_a_malformed_catalog_gives_the_same_error(client, harness):
    harness.catalog = {"families": [{"family": "gemini", "models": ["x"]}]}

    response = await client.get(f"{PREFIX}/settings/models")

    assert response.status_code == 503
