from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import app.mentor_memory as mentor_memory
from app.llm_client import get_mentor_response
from app.main import app
from app.schemas import MentorRequest

client = TestClient(app)

MOCK_LLM_RESPONSE = {
    "observation": "Tu as deja teste une premiere commande et tu compares maintenant les chemins.",
    "question": "Qu'est-ce qui change entre ta source et ta destination ?",
    "hint": "Observe le chemin courant avant et apres la copie.",
    "next_action": "Refais un test minimal avec un seul fichier et note le resultat.",
}


class FakeRedisStore:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.ttls: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        self.data[key] = value
        self.ttls[key] = ttl_seconds
        return True

    def keys(self, pattern: str) -> list[str]:
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return [key for key in self.data if key.startswith(prefix)]
        return [key for key in self.data if key == pattern]

    def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self.data:
                deleted += 1
                self.data.pop(key, None)
                self.ttls.pop(key, None)
        return deleted


def _build_fake_message(text: str) -> SimpleNamespace:
    return SimpleNamespace(content=[SimpleNamespace(text=text)])


def test_append_conversation_turn_trims_history(monkeypatch) -> None:
    store = FakeRedisStore()
    monkeypatch.setattr(mentor_memory, "get_conversation_store", lambda: store)
    monkeypatch.setenv("MENTOR_MEMORY_MAX_TURNS", "2")

    mentor_memory.append_conversation_turn(
        "learner-1",
        "shell-basics",
        user_question="Question 1",
        mentor_observation="Obs 1",
        mentor_question="Q 1",
        mentor_hint="Hint 1",
        mentor_next_action="Action 1",
    )
    mentor_memory.append_conversation_turn(
        "learner-1",
        "shell-basics",
        user_question="Question 2",
        mentor_observation="Obs 2",
        mentor_question="Q 2",
        mentor_hint="Hint 2",
        mentor_next_action="Action 2",
    )
    history = mentor_memory.append_conversation_turn(
        "learner-1",
        "shell-basics",
        user_question="Question 3",
        mentor_observation="Obs 3",
        mentor_question="Q 3",
        mentor_hint="Hint 3",
        mentor_next_action="Action 3",
    )

    assert len(history) == 2
    assert history[0]["user_question"] == "Question 2"
    assert history[1]["user_question"] == "Question 3"
    assert store.ttls["mentor:conv:learner-1:shell-basics"] == 1800


def test_clear_conversation_history_removes_all_module_keys_for_learner(monkeypatch) -> None:
    store = FakeRedisStore()
    monkeypatch.setattr(mentor_memory, "get_conversation_store", lambda: store)

    mentor_memory.append_conversation_turn(
        "learner-1",
        "shell-basics",
        user_question="Question 1",
        mentor_observation="Obs 1",
        mentor_question="Q 1",
        mentor_hint="Hint 1",
        mentor_next_action="Action 1",
    )
    mentor_memory.append_conversation_turn(
        "learner-1",
        "shell-streams",
        user_question="Question 2",
        mentor_observation="Obs 2",
        mentor_question="Q 2",
        mentor_hint="Hint 2",
        mentor_next_action="Action 2",
    )
    mentor_memory.append_conversation_turn(
        "learner-2",
        "shell-basics",
        user_question="Question 3",
        mentor_observation="Obs 3",
        mentor_question="Q 3",
        mentor_hint="Hint 3",
        mentor_next_action="Action 3",
    )

    deleted = mentor_memory.clear_conversation_history("learner-1")

    assert deleted == 2
    assert mentor_memory.load_conversation_history("learner-1", "shell-basics") == []
    assert len(mentor_memory.load_conversation_history("learner-2", "shell-basics")) == 1


def test_get_mentor_response_includes_recent_history_in_prompt() -> None:
    request = MentorRequest(
        learner_id="learner-1",
        track_id="shell",
        module_id="shell-basics",
        question="Je bloque encore sur cp",
        pace_mode="normal",
        phase="foundation",
    )
    fake_message = _build_fake_message(
        """
        {
          "observation": "Tu reprends le meme probleme avec plus de contexte.",
          "question": "Qu'as-tu observe sur le chemin de destination ?",
          "hint": "Compare la source et la destination ligne par ligne.",
          "next_action": "Refais un test minimal et note l'etat avant/apres."
        }
        """
    )
    fake_client = MagicMock()
    fake_client.messages.create.return_value = fake_message
    history = [
        mentor_memory.MentorTurn(
            timestamp="2026-03-29T12:00:00+00:00",
            user_question="Je bloque sur ls",
            mentor_observation="Tu regardes le contenu du dossier.",
            mentor_question="Quelle option as-tu deja testee ?",
            mentor_hint="Commence par une seule option.",
            mentor_next_action="Teste ls -la sur un dossier simple.",
        )
    ]

    with (
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False),
        patch("app.llm_client._build_anthropic_client", return_value=fake_client),
    ):
        get_mentor_response(
            request,
            "Shell 0 to Hero",
            "Shell Basics",
            "shell",
            conversation_history=history,
        )

    prompt = fake_client.messages.create.call_args.kwargs["messages"][0]["content"][0]["text"]
    assert "Historique recent de la session:" in prompt
    assert "Je bloque sur ls" in prompt
    assert "Teste ls -la sur un dossier simple." in prompt


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_mentor_respond_reuses_history_and_stores_new_turn(mock_llm, monkeypatch) -> None:
    store = FakeRedisStore()
    monkeypatch.setattr(mentor_memory, "get_conversation_store", lambda: store)

    mentor_memory.append_conversation_turn(
        "learner-1",
        "shell-basics",
        user_question="J'ai deja essaye cp",
        mentor_observation="Tu as deja fait un premier essai.",
        mentor_question="Quelle erreur as-tu vue ?",
        mentor_hint="Relis le chemin de destination.",
        mentor_next_action="Note le message d'erreur exact.",
    )

    response = client.post(
        "/api/v1/mentor/respond",
        json={
            "learner_id": "learner-1",
            "track_id": "shell",
            "module_id": "shell-basics",
            "question": "Je bloque toujours sur cp",
            "pace_mode": "normal",
            "phase": "foundation",
        },
    )

    assert response.status_code == 200
    _, _, _, active_course = mock_llm.call_args.args
    assert active_course == "shell"
    assert len(mock_llm.call_args.kwargs["conversation_history"]) == 1

    history = mentor_memory.load_conversation_history("learner-1", "shell-basics")
    assert len(history) == 2
    assert history[-1]["user_question"] == "Je bloque toujours sur cp"
    assert history[-1]["mentor_next_action"] == MOCK_LLM_RESPONSE["next_action"]


def test_clear_mentor_conversations_endpoint_deletes_all_keys(monkeypatch) -> None:
    store = FakeRedisStore()
    monkeypatch.setattr(mentor_memory, "get_conversation_store", lambda: store)

    mentor_memory.append_conversation_turn(
        "learner-1",
        "shell-basics",
        user_question="Question 1",
        mentor_observation="Obs 1",
        mentor_question="Q 1",
        mentor_hint="Hint 1",
        mentor_next_action="Action 1",
    )
    mentor_memory.append_conversation_turn(
        "learner-1",
        "shell-streams",
        user_question="Question 2",
        mentor_observation="Obs 2",
        mentor_question="Q 2",
        mentor_hint="Hint 2",
        mentor_next_action="Action 2",
    )

    response = client.delete("/api/v1/mentor/conversations/learner-1")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "learner_id": "learner-1", "deleted_keys": 2}
    assert mentor_memory.load_conversation_history("learner-1", "shell-basics") == []
