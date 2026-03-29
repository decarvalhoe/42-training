from unittest.mock import patch

import pytest

from app.main import health, mentor_respond
from app.schemas import MentorRequest

MOCK_LLM_RESPONSE = {
    "observation": "Tu travailles sur les bases shell.",
    "question": "Quelle commande as-tu essayee en premier?",
    "hint": "Regarde la page man de cp.",
    "next_action": "Essaie cp avec un seul fichier d'abord.",
}


@pytest.fixture(autouse=True)
def _patch_emit_event():
    with patch("app.main.emit_event", return_value=None):
        yield


def test_health() -> None:
    assert health() == {"status": "ok", "service": "ai_gateway"}


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_mentor_respond_with_llm(mock_llm) -> None:
    response = mentor_respond(
        MentorRequest(
            track_id="shell",
            module_id="shell-basics",
            question="Je bloque sur cp",
            pace_mode="normal",
            phase="foundation",
        )
    )
    assert response.status == "ok"
    assert response.observation == MOCK_LLM_RESPONSE["observation"]
    assert response.question == MOCK_LLM_RESPONSE["question"]
    assert response.hint == MOCK_LLM_RESPONSE["hint"]
    assert response.next_action == MOCK_LLM_RESPONSE["next_action"]
    assert response.direct_solution_allowed is False
    assert "official_42" in response.source_policy
    mock_llm.assert_called_once()


@patch("app.main.get_mentor_response", side_effect=RuntimeError("No API key"))
def test_mentor_respond_fallback(mock_llm) -> None:
    response = mentor_respond(
        MentorRequest(
            track_id="shell",
            module_id="shell-basics",
            question="Je bloque sur cp",
            pace_mode="normal",
            phase="foundation",
        )
    )
    assert response.status == "ok"
    assert "Tu travailles sur" in response.observation
    assert response.direct_solution_allowed is False
    mock_llm.assert_called_once()


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_mentor_respond_emits_event(mock_llm) -> None:
    with patch("app.main.emit_event", return_value=None) as mock_emit:
        response = mentor_respond(
            MentorRequest(
                track_id="shell",
                module_id="shell-basics",
                question="Je bloque sur cp",
                pace_mode="normal",
                phase="foundation",
            )
        )
    assert response.status == "ok"
    mock_emit.assert_called_once_with(
        "mentor_query",
        learner_id="default",
        track_id="shell",
        module_id="shell-basics",
        payload={
            "phase": "foundation",
            "pace_mode": "normal",
            "direct_solution_allowed": False,
            "response_source": "llm",
            "question_length": len("Je bloque sur cp"),
        },
    )
    mock_llm.assert_called_once()


def test_mentor_respond_advanced_allows_solution() -> None:
    with patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE):
        response = mentor_respond(
            MentorRequest(
                track_id="shell",
                module_id="shell-basics",
                question="Montre-moi comment fonctionne cp -r",
                pace_mode="normal",
                phase="advanced",
            )
        )
        assert response.direct_solution_allowed is True


@patch("app.main.get_mentor_response", return_value={"observation": "incomplete"})
def test_mentor_respond_fallback_on_invalid_llm_payload(mock_llm) -> None:
    response = mentor_respond(
        MentorRequest(
            track_id="shell",
            module_id="shell-basics",
            question="Je bloque sur cp",
            pace_mode="normal",
            phase="foundation",
        )
    )
    assert "Tu travailles sur" in response.observation
    assert response.question
    assert response.hint
    assert response.next_action
    mock_llm.assert_called_once()
