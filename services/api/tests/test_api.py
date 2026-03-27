from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "api"


def test_tracks() -> None:
    response = client.get("/api/v1/tracks")
    assert response.status_code == 200
    data = response.json()
    assert any(track["id"] == "shell" for track in data)
