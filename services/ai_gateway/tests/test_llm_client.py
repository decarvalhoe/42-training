from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.llm_client import get_defense_evaluation, get_mentor_response
from app.schemas import MentorRequest


def _build_fake_message(text: str) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(text=text)])


def test_get_mentor_response_calls_anthropic_sdk() -> None:
    request = MentorRequest(
        track_id="shell",
        module_id="shell-basics",
        question="Je bloque sur cp",
        pace_mode="normal",
        phase="foundation",
    )
    fake_message = _build_fake_message(
        """
        {
          "observation": "Tu travailles sur les bases shell.",
          "question": "Quelle commande as-tu deja essayee ?",
          "hint": "Observe d'abord la source et la destination.",
          "next_action": "Teste cp sur un fichier simple."
        }
        """
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message

    with (
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False),
        patch("app.llm_client._build_anthropic_client", return_value=fake_client) as mock_builder,
    ):
        response = get_mentor_response(request, "Shell 0 to Hero", "Shell Basics", "shell")

    assert response == {
        "observation": "Tu travailles sur les bases shell.",
        "question": "Quelle commande as-tu deja essayee ?",
        "hint": "Observe d'abord la source et la destination.",
        "next_action": "Teste cp sur un fichier simple.",
    }
    mock_builder.assert_called_once_with("test-key")
    fake_client.messages.create.assert_called_once()
    kwargs = fake_client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-20250514"
    assert "Tu es un mentor pedagogique" in kwargs["system"]
    assert kwargs["messages"][0]["content"][0]["text"].startswith("Track: shell")


def test_get_mentor_response_requires_api_key() -> None:
    request = MentorRequest(question="Je bloque sur cp")

    with patch.dict("os.environ", {}, clear=True), pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY not set"):
        get_mentor_response(request, "Shell 0 to Hero", "Shell Basics", "shell")


def test_get_mentor_response_rejects_invalid_json() -> None:
    request = MentorRequest(question="Je bloque sur cp")
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _build_fake_message("pas du json")

    with (
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False),
        patch("app.llm_client._build_anthropic_client", return_value=fake_client),
        pytest.raises(ValueError),
    ):
        get_mentor_response(request, "Shell 0 to Hero", "Shell Basics", "shell")


def test_get_mentor_response_rejects_missing_required_field() -> None:
    request = MentorRequest(question="Je bloque sur cp")
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _build_fake_message(
        """
        {
          "observation": "Tu bloques sur cp.",
          "question": "Quelle commande as-tu testee ?",
          "hint": "Observe les chemins."
        }
        """
    )

    with (
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False),
        patch("app.llm_client._build_anthropic_client", return_value=fake_client),
        pytest.raises(ValueError, match="next_action"),
    ):
        get_mentor_response(request, "Shell 0 to Hero", "Shell Basics", "shell")


def test_get_defense_evaluation_calls_anthropic_sdk() -> None:
    fake_message = _build_fake_message(
        """
        {
          "score": 0.82,
          "feedback": "Bonne comprehension globale. Il manque encore un exemple concret pour montrer la maitrise."
        }
        """
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message

    with (
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False),
        patch("app.llm_client._build_anthropic_client", return_value=fake_client) as mock_builder,
    ):
        response = get_defense_evaluation(
            track_id="shell",
            module_id="shell-basics",
            phase="foundation",
            question_text="Explain ls",
            skill="ls",
            expected_keywords=["list", "files", "directory"],
            answer="ls liste les fichiers d'un dossier et me permet de verifier l'etat courant du filesystem.",
        )

    assert response == {
        "score": 0.82,
        "feedback": "Bonne comprehension globale. Il manque encore un exemple concret pour montrer la maitrise.",
    }
    mock_builder.assert_called_once_with("test-key")
    fake_client.messages.create.assert_called_once()
    kwargs = fake_client.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-sonnet-4-20250514"
    assert "examinateur de defense orale" in kwargs["system"]
    assert "Question de defense: Explain ls" in kwargs["messages"][0]["content"][0]["text"]


def test_get_defense_evaluation_rejects_out_of_range_score() -> None:
    fake_client = MagicMock()
    fake_client.messages.create.return_value = _build_fake_message(
        """
        {
          "score": 1.4,
          "feedback": "Trop genereux."
        }
        """
    )

    with (
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False),
        patch("app.llm_client._build_anthropic_client", return_value=fake_client),
        pytest.raises(ValueError, match=r"between 0\.0 and 1\.0"),
    ):
        get_defense_evaluation(
            track_id="shell",
            module_id="shell-basics",
            phase="foundation",
            question_text="Explain ls",
            skill="ls",
            expected_keywords=["list", "files", "directory"],
            answer="ls liste les fichiers.",
        )
