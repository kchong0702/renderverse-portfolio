from fastapi.testclient import TestClient

from src.app.app import create_app


def test_health():
    response = TestClient(create_app()).get("/artifact-service/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
