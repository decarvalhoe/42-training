"""Tests for the intent router endpoint and classifier."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.intent import classify_intent_fallback, route_intent
from app.main import app
from app.schemas import IntentRequest

client = TestClient(app)
ENDPOINT = "/api/v1/intent"


def _build_fake_message(text: str) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(text=text)])


def test_intent_routes_general_help_to_mentor() -> None:
    response = client.post(
        ENDPOINT,
        json={"message": "Je bloque sur les pointeurs, quel petit test je peux faire ensuite ?"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["active_role"] == "mentor"
    assert data["route"] == "/api/v1/mentor/respond"


def test_intent_routes_resource_request_to_librarian() -> None:
    response = client.post(
        ENDPOINT,
        json={"message": "Trouve-moi une doc officielle ou une ressource sur norminette."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active_role"] == "librarian"
    assert data["route"] == "/api/v1/librarian/search"


def test_intent_routes_code_review_to_reviewer() -> None:
    response = client.post(
        ENDPOINT,
        json={"message": "Peux-tu reviewer ce code ? ```c\nint main(void) { return 0; }\n```"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active_role"] == "reviewer"
    assert data["route"] == "/api/v1/reviewer/review"


def test_intent_routes_defense_request_to_examiner() -> None:
    response = client.post(
        ENDPOINT,
        json={"message": "Fais-moi passer une mini defense orale sur malloc."},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["active_role"] == "examiner"
    assert data["route"] == "/api/v1/defense/start"


def test_intent_rejects_message_too_short() -> None:
    response = client.post(ENDPOINT, json={"message": "hi"})
    assert response.status_code == 422


def test_route_intent_uses_llm_when_available() -> None:
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _build_fake_message(
        """
        {
          "active_role": "librarian",
          "reason": "La demande cherche explicitement une documentation.",
          "confidence": 0.93
        }
        """
    )

    with (
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False),
        patch("app.intent._build_anthropic_client", return_value=fake_client),
    ):
        result = route_intent(IntentRequest(message="Je cherche la documentation officielle sur malloc"))

    assert result["active_role"] == "librarian"
    assert result["classifier"] == "llm"
    assert result["route"] == "/api/v1/librarian/search"
    assert result["confidence"] == 0.93


def test_route_intent_falls_back_when_llm_payload_is_invalid() -> None:
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _build_fake_message("pas du json")

    with (
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False),
        patch("app.intent._build_anthropic_client", return_value=fake_client),
    ):
        result = route_intent(IntentRequest(message="Peux-tu reviewer ce code ? ```python\nprint('x')\n```"))

    assert result["active_role"] == "reviewer"
    assert result["classifier"] == "fallback"


def test_fallback_classifier_defaults_to_mentor_when_signal_is_weak() -> None:
    result = classify_intent_fallback(IntentRequest(message="Je voudrais avancer sur ce module."))
    assert result["active_role"] == "mentor"
    assert result["confidence"] >= 0.55


def test_fallback_classifier_prefers_examiner_for_quiz_requests() -> None:
    result = classify_intent_fallback(IntentRequest(message="Quiz me on pointers before my oral defense."))
    assert result["active_role"] == "examiner"
