from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

MOCK_LLM_RESPONSE = {
    "observation": "Tu travailles sur les bases shell.",
    "question": "Quelle commande as-tu essayee en premier?",
    "hint": "Regarde la page man de cp.",
    "next_action": "Essaie cp avec un seul fichier d'abord.",
}


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "ai_gateway"


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_mentor_respond_with_llm(mock_llm) -> None:
    response = client.post(
        "/api/v1/mentor/respond",
        json={
            "track_id": "shell",
            "module_id": "shell-basics",
            "question": "Je bloque sur cp",
            "pace_mode": "normal",
            "phase": "foundation",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["observation"] == MOCK_LLM_RESPONSE["observation"]
    assert data["question"] == MOCK_LLM_RESPONSE["question"]
    assert data["hint"] == MOCK_LLM_RESPONSE["hint"]
    assert data["next_action"] == MOCK_LLM_RESPONSE["next_action"]
    assert data["direct_solution_allowed"] is False
    assert "official_42" in data["source_policy"]
    mock_llm.assert_called_once()


@patch("app.main.get_mentor_response", side_effect=RuntimeError("No API key"))
def test_mentor_respond_fallback(mock_llm) -> None:
    response = client.post(
        "/api/v1/mentor/respond",
        json={
            "track_id": "shell",
            "module_id": "shell-basics",
            "question": "Je bloque sur cp",
            "pace_mode": "normal",
            "phase": "foundation",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Tu travailles sur" in data["observation"]
    assert data["direct_solution_allowed"] is False


def test_mentor_respond_advanced_allows_solution() -> None:
    with patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE):
        response = client.post(
            "/api/v1/mentor/respond",
            json={
                "track_id": "shell",
                "module_id": "shell-basics",
                "question": "Montre-moi comment fonctionne cp -r",
                "pace_mode": "normal",
                "phase": "advanced",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["direct_solution_allowed"] is True
