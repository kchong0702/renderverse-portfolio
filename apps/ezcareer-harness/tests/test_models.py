from fastapi.testclient import TestClient

from src.app.app import create_app


def test_models_lists_what_a_user_can_pick_by_family():
    response = TestClient(create_app()).get("/ezcareer/models")

    assert response.status_code == 200
    assert response.json() == {
        "families": [
            {"family": "glm", "models": ["glm-5.3"]},
            {"family": "claude", "models": ["claude-opus-5-5", "claude-sonnet-5-5"]},
            {"family": "openai", "models": ["gpt-6-luna"]},
        ]
    }
