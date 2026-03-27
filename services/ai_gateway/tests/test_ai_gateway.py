from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "ai_gateway"


def test_mentor_response() -> None:
    response = client.post(
        "/api/v1/mentor/respond",
        json={
            "track_id": "shell",
            "module_id": "shell-basics",
            "question": "Je bloque sur cp",
            "pace_mode": "normal",
            "phase": "foundation"
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["direct_solution_allowed"] is False
