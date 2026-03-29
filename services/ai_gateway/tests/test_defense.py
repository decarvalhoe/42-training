"""Tests for the oral defense MVP flow (#38).

Tests cover the full lifecycle: start session, answer questions, get results.
Key invariants:
- Questions are Socratic — they never reveal answers
- Scoring rewards explanation depth, not keyword recitation
- The system never provides correct answers in feedback
"""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import defense_persistence
from app.defense import DefenseQuestion, _generate_questions, clear_sessions, score_answer
from app.main import app
from app.terminal_context import TerminalContext, capture_terminal_context

client = TestClient(app)

START_ENDPOINT = "/api/v1/defense/start"
ANSWER_ENDPOINT = "/api/v1/defense/answer"


class _FakeHttpxResponse:
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self._payload = payload

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise defense_persistence.httpx.HTTPError("fake error")


@pytest.fixture(autouse=True)
def _fake_persistence_backend(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    store: dict[str, Any] = {
        "defense_sessions": {},
        "review_attempts": [],
    }

    def fake_post(url: str, json: dict[str, Any], timeout: float) -> _FakeHttpxResponse:
        if url.endswith("/api/v1/defense-sessions"):
            session_id = json["session_id"]
            if session_id in store["defense_sessions"]:
                return _FakeHttpxResponse(409, {"detail": "Defense session already exists"})
            store["defense_sessions"][session_id] = dict(json)
            return _FakeHttpxResponse(201, dict(json))

        if url.endswith("/api/v1/review-attempts"):
            payload = dict(json)
            payload["id"] = f"review-{len(store['review_attempts']) + 1}"
            store["review_attempts"].append(payload)
            return _FakeHttpxResponse(201, payload)

        raise AssertionError(f"Unexpected POST url in defense persistence test: {url}")

    def fake_put(url: str, json: dict[str, Any], timeout: float) -> _FakeHttpxResponse:
        session_id = url.rsplit("/", 1)[-1]
        existing = store["defense_sessions"].get(session_id)
        if existing is None:
            return _FakeHttpxResponse(404, {"detail": "Defense session not found"})

        updated = dict(existing)
        updated.update(json)
        updated["session_id"] = session_id
        store["defense_sessions"][session_id] = updated
        return _FakeHttpxResponse(200, updated)

    def fake_get(url: str, timeout: float) -> _FakeHttpxResponse:
        session_id = url.rsplit("/", 1)[-1]
        payload = store["defense_sessions"].get(session_id)
        if payload is None:
            return _FakeHttpxResponse(404, {"detail": "Defense session not found"})
        return _FakeHttpxResponse(200, dict(payload))

    monkeypatch.setattr(defense_persistence.httpx, "post", fake_post)
    monkeypatch.setattr(defense_persistence.httpx, "put", fake_put)
    monkeypatch.setattr(defense_persistence.httpx, "get", fake_get)
    return store


@pytest.fixture(autouse=True)
def _clean_sessions():
    """Clear in-memory sessions between tests."""
    clear_sessions()
    yield
    clear_sessions()


def _start_session(
    track_id: str = "shell",
    module_id: str = "shell-basics",
    learner_id: str | None = None,
    reviewer_id: str | None = None,
    num_questions: int = 3,
    question_time_limit_seconds: int = 60,
) -> dict:
    response = client.post(
        START_ENDPOINT,
        json={
            "track_id": track_id,
            "module_id": module_id,
            "learner_id": learner_id,
            "reviewer_id": reviewer_id,
            "num_questions": num_questions,
            "question_time_limit_seconds": question_time_limit_seconds,
        },
    )
    assert response.status_code == 200
    return response.json()


# === Start session ===


def test_start_session_returns_questions() -> None:
    data = _start_session()
    assert data["status"] == "ok"
    assert data["session_id"]
    assert data["track_id"] == "shell"
    assert data["module_id"] == "shell-basics"
    assert len(data["questions"]) == 3
    assert data["total_questions"] == 3
    assert data["question_time_limit_seconds"] == 60
    assert data["active_question_id"] == data["questions"][0]["question_id"]
    assert data["current_question_deadline"] is not None


def test_start_session_questions_have_structure() -> None:
    data = _start_session()
    for q in data["questions"]:
        assert "question_id" in q
        assert "text" in q
        assert "skill" in q
        assert q["time_limit_seconds"] == 60
        assert len(q["text"]) > 10


def test_start_session_questions_are_socratic() -> None:
    """Questions should ask the learner to explain, not reveal answers."""
    data = _start_session()
    for q in data["questions"]:
        text_lower = q["text"].lower()
        # Should contain explanation-seeking language
        assert any(word in text_lower for word in ["explain", "what", "how", "describe", "demonstrate"]), (
            f"Question should be Socratic: {q['text']}"
        )


def test_start_session_custom_num_questions() -> None:
    data = _start_session(num_questions=2)
    assert len(data["questions"]) == 2


def test_start_session_c_track() -> None:
    data = _start_session(track_id="c", module_id="c-memory")
    assert data["track_id"] == "c"
    assert len(data["questions"]) > 0


def test_start_session_python_track() -> None:
    data = _start_session(track_id="python_ai", module_id="python-basics")
    assert data["track_id"] == "python_ai"
    assert len(data["questions"]) > 0


def test_start_session_invalid_track() -> None:
    response = client.post(
        START_ENDPOINT,
        json={"track_id": "nonexistent", "module_id": "x"},
    )
    assert response.status_code == 404


def test_start_session_invalid_module() -> None:
    response = client.post(
        START_ENDPOINT,
        json={"track_id": "shell", "module_id": "nonexistent"},
    )
    assert response.status_code == 404


def test_start_session_persists_backend_record(_fake_persistence_backend: dict[str, Any]) -> None:
    data = _start_session(learner_id="learner-1")
    persisted = _fake_persistence_backend["defense_sessions"][data["session_id"]]
    assert persisted["learner_id"] == "learner-1"
    assert persisted["status"] == "in_progress"
    assert persisted["questions"] == [question["text"] for question in data["questions"]]
    assert persisted["evidence_artifacts"][0]["type"] == "defense_session_state"
    assert persisted["evidence_artifacts"][0]["track_id"] == "shell"


# === Answer questions ===


def test_answer_question_scores_good_answer() -> None:
    session = _start_session()
    q = session["questions"][0]
    response = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": q["question_id"],
            "answer": f"The command {q['skill']} is used to list files in a directory. "
            f"For example, if I run ls in my home directory, it shows all visible files. "
            f"This is important because it lets me verify the current state of the filesystem.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["score"] > 0.0
    assert data["feedback"]
    assert data["questions_remaining"] == 2
    assert data["timed_out"] is False
    assert data["elapsed_seconds"] >= 0.0
    assert data["next_question_id"] == session["questions"][1]["question_id"]
    assert data["next_question_deadline"] is not None


def test_answer_question_scores_brief_answer_low() -> None:
    session = _start_session()
    q = session["questions"][0]
    response = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": q["question_id"],
            "answer": "I dunno",
        },
    )
    data = response.json()
    assert data["score"] == 0.0


def test_answer_question_feedback_never_reveals_answer() -> None:
    """Feedback must guide, not provide the correct answer."""
    session = _start_session()
    q = session["questions"][0]
    response = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": q["question_id"],
            "answer": "I'm not sure about this concept at all really.",
        },
    )
    data = response.json()
    feedback_lower = data["feedback"].lower()
    # Should not contain solution-like language
    assert "the answer is" not in feedback_lower
    assert "the correct" not in feedback_lower
    assert "you should have said" not in feedback_lower


def test_answer_already_answered_rejected() -> None:
    session = _start_session()
    q = session["questions"][0]
    payload = {
        "session_id": session["session_id"],
        "question_id": q["question_id"],
        "answer": "The command is used to navigate the filesystem because it changes directory.",
    }
    client.post(ANSWER_ENDPOINT, json=payload)
    response = client.post(ANSWER_ENDPOINT, json=payload)
    assert response.status_code == 409


def test_answer_invalid_session() -> None:
    response = client.post(
        ANSWER_ENDPOINT,
        json={"session_id": "nonexistent", "question_id": "q-1", "answer": "test answer here"},
    )
    assert response.status_code == 404


def test_answer_invalid_question() -> None:
    session = _start_session()
    response = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": "nonexistent",
            "answer": "test answer here for question",
        },
    )
    assert response.status_code == 404


def test_answer_requires_current_question_first() -> None:
    session = _start_session(num_questions=2)
    second_question = session["questions"][1]
    response = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": second_question["question_id"],
            "answer": "I want to skip ahead and answer this one first.",
        },
    )
    assert response.status_code == 409


def test_answer_decrements_remaining() -> None:
    session = _start_session(num_questions=2)
    q0, q1 = session["questions"]

    resp1 = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": q0["question_id"],
            "answer": "This command lists files in the current directory because it reads the directory entries.",
        },
    )
    assert resp1.json()["questions_remaining"] == 1

    resp2 = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": q1["question_id"],
            "answer": "This command changes the current working directory so I can navigate the filesystem tree.",
        },
    )
    assert resp2.json()["questions_remaining"] == 0


# === Session result ===


def test_result_after_all_answered() -> None:
    session = _start_session(num_questions=2)
    for q in session["questions"]:
        client.post(
            ANSWER_ENDPOINT,
            json={
                "session_id": session["session_id"],
                "question_id": q["question_id"],
                "answer": f"The command {q['skill']} is essential for working with files. "
                f"For example, I use it every day because it helps me manage the filesystem efficiently.",
            },
        )

    response = client.get(f"/api/v1/defense/{session['session_id']}/result")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["session_id"] == session["session_id"]
    assert 0.0 <= data["overall_score"] <= 1.0
    assert isinstance(data["passed"], bool)
    assert data["summary"]
    assert len(data["question_results"]) == 2


def test_answer_reloads_session_from_persistence_after_local_cache_clear(
    _fake_persistence_backend: dict[str, Any],
) -> None:
    session = _start_session(learner_id="learner-1", num_questions=1)
    question = session["questions"][0]
    clear_sessions()

    response = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": question["question_id"],
            "answer": "pwd prints the current working directory because it tells me exactly where I am before I run another command.",
        },
    )

    assert response.status_code == 200
    persisted = _fake_persistence_backend["defense_sessions"][session["session_id"]]
    assert persisted["answers"] == [
        "pwd prints the current working directory because it tells me exactly where I am before I run another command."
    ]
    assert persisted["status"] in {"passed", "failed"}
    state = persisted["evidence_artifacts"][0]
    assert state["questions"][0]["answered"] is True
    assert state["questions"][0]["answer"].startswith("pwd prints the current working directory")


def test_completed_session_creates_review_attempt_when_profile_present(
    _fake_persistence_backend: dict[str, Any],
) -> None:
    session = _start_session(learner_id="learner-1", num_questions=1)
    question = session["questions"][0]

    response = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": question["question_id"],
            "answer": "ls lists files in a directory because it reads the directory entries. For example, I use it to inspect the current folder before copying files.",
        },
    )

    assert response.status_code == 200
    review_attempts = _fake_persistence_backend["review_attempts"]
    assert len(review_attempts) == 1
    review_attempt = review_attempts[0]
    assert review_attempt["learner_id"] == "learner-1"
    assert review_attempt["reviewer_id"] == "learner-1"
    assert review_attempt["module_id"] == "shell-basics"
    assert review_attempt["evidence_artifacts"][0]["session_id"] == session["session_id"]


def test_result_reads_persisted_session_when_local_cache_is_empty() -> None:
    session = _start_session(num_questions=1)
    question = session["questions"][0]
    answer_response = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": question["question_id"],
            "answer": "This command helps me inspect files in the current directory because it exposes the current filesystem state.",
        },
    )
    assert answer_response.status_code == 200

    clear_sessions()
    response = client.get(f"/api/v1/defense/{session['session_id']}/result")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session["session_id"]
    assert len(data["question_results"]) == 1


def test_result_partial_answers() -> None:
    session = _start_session(num_questions=2)
    q = session["questions"][0]
    client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": q["question_id"],
            "answer": "This command helps with files because it allows managing the filesystem.",
        },
    )

    response = client.get(f"/api/v1/defense/{session['session_id']}/result")
    data = response.json()
    assert data["passed"] is False
    assert "incomplete" in data["summary"].lower() or "unanswered" in data["summary"].lower()


def test_result_no_answers() -> None:
    session = _start_session()
    response = client.get(f"/api/v1/defense/{session['session_id']}/result")
    data = response.json()
    assert data["overall_score"] == 0.0
    assert data["passed"] is False


def test_result_invalid_session() -> None:
    response = client.get("/api/v1/defense/nonexistent/result")
    assert response.status_code == 404


def test_completed_session_rejects_answers() -> None:
    session = _start_session(num_questions=1)
    q = session["questions"][0]
    client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": q["question_id"],
            "answer": "This concept is fundamental because it allows filesystem navigation.",
        },
    )
    # Session should be completed now, new answer should fail
    response = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": q["question_id"],
            "answer": "another try at the explanation",
        },
    )
    assert response.status_code == 400


def test_answer_times_out_when_question_deadline_passed() -> None:
    start = datetime(2026, 3, 29, 12, 0, 0, tzinfo=UTC)
    with patch("app.defense._utc_now", return_value=start):
        session = _start_session(num_questions=1, question_time_limit_seconds=30)

    question = session["questions"][0]
    with patch("app.defense._utc_now", return_value=start + timedelta(seconds=45)):
        response = client.post(
            ANSWER_ENDPOINT,
            json={
                "session_id": session["session_id"],
                "question_id": question["question_id"],
                "answer": "pwd shows the current directory and helps me verify where I am in the filesystem.",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["timed_out"] is True
    assert data["score"] == 0.0
    assert data["elapsed_seconds"] == 45.0
    assert data["next_question_id"] is None
    assert data["next_question_deadline"] is None


def test_result_counts_timed_out_questions() -> None:
    start = datetime(2026, 3, 29, 12, 0, 0, tzinfo=UTC)
    with patch("app.defense._utc_now", return_value=start):
        session = _start_session(num_questions=1, question_time_limit_seconds=20)

    question = session["questions"][0]
    with patch("app.defense._utc_now", return_value=start + timedelta(seconds=25)):
        client.post(
            ANSWER_ENDPOINT,
            json={
                "session_id": session["session_id"],
                "question_id": question["question_id"],
                "answer": "ls lists files in a directory because it reads the directory entries.",
            },
        )

    response = client.get(f"/api/v1/defense/{session['session_id']}/result")
    data = response.json()
    assert data["timed_out_questions"] == 1
    assert data["question_results"][0]["timed_out"] is True
    assert "timer" in data["summary"].lower()


# === Unit tests for scoring ===


def test_score_rewards_explanation() -> None:
    q = DefenseQuestion(id="q-1", text="Explain ls", skill="ls", expected_keywords=["list", "files", "directory"])
    score, _ = score_answer(
        q, "The ls command is used to list files in a directory because it reads directory entries."
    )
    assert score >= 0.5


def test_score_answer_uses_llm_when_api_key_available() -> None:
    q = DefenseQuestion(id="q-1", text="Explain ls", skill="ls", expected_keywords=["list", "files", "directory"])

    with (
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False),
        patch(
            "app.defense.get_defense_evaluation",
            return_value={"score": 0.91, "feedback": "Bonne maitrise, ajoute encore un exemple concret."},
        ) as mock_evaluation,
    ):
        score, feedback = score_answer(
            q,
            "ls liste les fichiers d'un dossier et permet de verifier rapidement l'etat du repertoire courant.",
            track_id="shell",
            module_id="shell-basics",
            phase="foundation",
        )

    assert score == 0.91
    assert feedback == "Bonne maitrise, ajoute encore un exemple concret."
    mock_evaluation.assert_called_once_with(
        track_id="shell",
        module_id="shell-basics",
        phase="foundation",
        question_text="Explain ls",
        skill="ls",
        expected_keywords=["list", "files", "directory"],
        answer="ls liste les fichiers d'un dossier et permet de verifier rapidement l'etat du repertoire courant.",
    )


def test_score_answer_falls_back_to_rule_based_when_llm_fails() -> None:
    q = DefenseQuestion(id="q-1", text="Explain ls", skill="ls", expected_keywords=["list", "files", "directory"])

    with (
        patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}, clear=False),
        patch("app.defense.get_defense_evaluation", side_effect=RuntimeError("Claude unavailable")),
    ):
        score, feedback = score_answer(
            q,
            "The ls command is used to list files in a directory because it reads directory entries.",
            track_id="shell",
            module_id="shell-basics",
            phase="foundation",
        )

    assert score >= 0.5
    assert "understanding" in feedback.lower() or "explanation" in feedback.lower()


def test_score_rewards_examples() -> None:
    q = DefenseQuestion(id="q-1", text="Explain ls", skill="ls", expected_keywords=["list", "files", "directory"])
    score_with, _ = score_answer(
        q, "ls lists files. For example, ls -la shows hidden files and permissions in a directory."
    )
    score_without, _ = score_answer(q, "ls lists files in the directory and shows what is there.")
    assert score_with > score_without


def test_score_penalizes_brief() -> None:
    q = DefenseQuestion(id="q-1", text="Explain ls", skill="ls", expected_keywords=["list", "files"])
    score, feedback = score_answer(q, "it lists")
    assert score == 0.0
    assert "brief" in feedback.lower() or "explain" in feedback.lower()


def test_result_question_results_structure() -> None:
    session = _start_session(num_questions=1)
    q = session["questions"][0]
    client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": q["question_id"],
            "answer": "This is about managing files in the filesystem because I need to organize my work.",
        },
    )
    response = client.get(f"/api/v1/defense/{session['session_id']}/result")
    data = response.json()
    qr = data["question_results"][0]
    assert "question_id" in qr
    assert "question" in qr
    assert "skill" in qr
    assert "score" in qr
    assert "feedback" in qr
    assert "answered" in qr
    assert "timed_out" in qr
    assert "elapsed_seconds" in qr


# === Resume interrupted session ===

RESUME_ENDPOINT = "/api/v1/defense/resume"


def test_resume_interrupted_session_after_cache_clear(
    _fake_persistence_backend: dict[str, Any],
) -> None:
    """Resuming a session whose in-memory state was lost reloads from persistence."""
    session = _start_session(learner_id="learner-1", num_questions=2)
    first_question = session["questions"][0]
    client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": first_question["question_id"],
            "answer": "pwd prints the current working directory because it tells me exactly where I am.",
        },
    )
    clear_sessions()

    response = client.post(RESUME_ENDPOINT, json={"session_id": session["session_id"]})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["session_id"] == session["session_id"]
    assert data["questions_answered"] == 1
    assert data["completed"] is False
    assert data["active_question_id"] == session["questions"][1]["question_id"]
    assert data["current_question_deadline"] is not None


def test_resume_completed_session() -> None:
    session = _start_session(num_questions=1)
    q = session["questions"][0]
    client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": q["question_id"],
            "answer": "This concept is fundamental because it allows filesystem navigation.",
        },
    )
    clear_sessions()

    response = client.post(RESUME_ENDPOINT, json={"session_id": session["session_id"]})
    assert response.status_code == 200
    data = response.json()
    assert data["completed"] is True
    assert data["active_question_id"] is None
    assert data["current_question_deadline"] is None


def test_resume_nonexistent_session() -> None:
    response = client.post(RESUME_ENDPOINT, json={"session_id": "does-not-exist"})
    assert response.status_code == 404


def test_resume_then_continue_answering(
    _fake_persistence_backend: dict[str, Any],
) -> None:
    """After resume, the learner can continue answering remaining questions."""
    session = _start_session(learner_id="learner-1", num_questions=2)
    first_question = session["questions"][0]
    client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": first_question["question_id"],
            "answer": "pwd prints the current working directory because it helps me navigate.",
        },
    )
    clear_sessions()

    client.post(RESUME_ENDPOINT, json={"session_id": session["session_id"]})

    second_question = session["questions"][1]
    response = client.post(
        ANSWER_ENDPOINT,
        json={
            "session_id": session["session_id"],
            "question_id": second_question["question_id"],
            "answer": "ls lists files in a directory because it reads the directory entries. For example, ls -la shows hidden files.",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["questions_remaining"] == 0

    result_response = client.get(f"/api/v1/defense/{session['session_id']}/result")
    result_data = result_response.json()
    assert len(result_data["question_results"]) == 2


def test_resume_resets_question_timer(
    _fake_persistence_backend: dict[str, Any],
) -> None:
    """Resuming should give a fresh deadline for the current question."""
    start = datetime(2026, 3, 29, 12, 0, 0, tzinfo=UTC)
    with patch("app.defense._utc_now", return_value=start):
        session = _start_session(num_questions=2, question_time_limit_seconds=30)

    first_question = session["questions"][0]
    with patch("app.defense._utc_now", return_value=start + timedelta(seconds=10)):
        client.post(
            ANSWER_ENDPOINT,
            json={
                "session_id": session["session_id"],
                "question_id": first_question["question_id"],
                "answer": "pwd prints the current working directory because it helps me know where I am.",
            },
        )

    clear_sessions()

    resume_time = start + timedelta(minutes=30)
    with patch("app.defense._utc_now", return_value=resume_time):
        response = client.post(RESUME_ENDPOINT, json={"session_id": session["session_id"]})

    data = response.json()
    deadline_str = data["current_question_deadline"]
    assert deadline_str is not None
    deadline = datetime.fromisoformat(deadline_str)
    expected_deadline = resume_time + timedelta(seconds=30)
    assert abs((deadline - expected_deadline).total_seconds()) < 2


# === Retry on transient persistence failures ===


def test_retry_recovers_from_transient_post_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Persistence retries on 5xx and succeeds on subsequent attempt."""
    call_count = 0
    original_post = defense_persistence.httpx.post

    def flaky_post(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return _FakeHttpxResponse(503, {"detail": "Service unavailable"})
        return original_post(*args, **kwargs)

    monkeypatch.setattr(defense_persistence, "RETRY_BASE_DELAY", 0.01)
    monkeypatch.setattr(defense_persistence.httpx, "post", flaky_post)

    response = client.post(
        START_ENDPOINT,
        json={"track_id": "shell", "module_id": "shell-basics"},
    )
    assert response.status_code == 200
    assert call_count >= 2


def test_retry_exhaustion_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    """After all retries are exhausted, the endpoint returns 503."""

    def always_fail(*args: Any, **kwargs: Any) -> _FakeHttpxResponse:
        return _FakeHttpxResponse(503, {"detail": "Service unavailable"})

    monkeypatch.setattr(defense_persistence, "RETRY_BASE_DELAY", 0.01)
    monkeypatch.setattr(defense_persistence.httpx, "post", always_fail)

    response = client.post(
        START_ENDPOINT,
        json={"track_id": "shell", "module_id": "shell-basics"},
    )
    assert response.status_code == 503


def test_retry_recovers_from_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Persistence retries on timeout exception and succeeds on retry."""
    import httpx as real_httpx

    call_count = 0
    original_get = defense_persistence.httpx.get

    def flaky_get(*args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise real_httpx.ConnectError("Connection refused")
        return original_get(*args, **kwargs)

    session = _start_session(num_questions=1)

    monkeypatch.setattr(defense_persistence, "RETRY_BASE_DELAY", 0.01)
    monkeypatch.setattr(defense_persistence.httpx, "get", flaky_get)

    response = client.get(f"/api/v1/defense/{session['session_id']}/result")
    assert response.status_code == 200
    assert call_count >= 2


# === Terminal context capture ===


def test_capture_terminal_context_returns_none_without_tmux() -> None:
    """When tmux is not available, capture returns None gracefully."""
    result = capture_terminal_context()
    # In CI/test environment, tmux session won't exist
    assert result is None


def test_terminal_context_as_prompt_block() -> None:
    ctx = TerminalContext(
        cwd="/home/learner/shell_03",
        git_status="M  sed_transform.sh",
        panes={"work": "$ grep -E '^host=' config.conf\nhost=localhost"},
        git_diff_summary=" sed_transform.sh | 3 +++",
    )
    block = ctx.as_prompt_block()
    assert "/home/learner/shell_03" in block
    assert "sed_transform.sh" in block
    assert "grep -E" in block
    assert not ctx.is_empty()


def test_terminal_context_empty() -> None:
    ctx = TerminalContext()
    assert ctx.is_empty()
    assert ctx.as_prompt_block() == ""


# === Context-aware question generation ===


def _shell_track() -> dict[str, Any]:
    return {"id": "shell"}


def _shell_module() -> dict[str, Any]:
    return {
        "id": "shell-basics",
        "skills": ["pwd", "ls", "cd"],
        "objectives": [],
        "exit_criteria": [],
    }


def test_generate_questions_with_terminal_context_references_cwd() -> None:
    """When terminal context is provided, questions reference the cwd."""
    ctx = TerminalContext(
        cwd="/home/learner/shell_03",
        panes={"work": "$ ls -la\ntotal 8\ndrwxr-xr-x 2 learner learner 4096 Mar 29 12:00 ."},
    )
    questions = _generate_questions(_shell_track(), _shell_module(), "foundation", 3, ctx)
    assert len(questions) == 3
    # At least one question should reference the cwd
    texts = " ".join(q.text for q in questions)
    assert "/home/learner/shell_03" in texts


def test_generate_questions_without_context_uses_generic_templates() -> None:
    """Without terminal context, generic Socratic templates are used."""
    questions = _generate_questions(_shell_track(), _shell_module(), "foundation", 3, None)
    assert len(questions) == 3
    texts = " ".join(q.text for q in questions)
    # Generic templates use "Explain in your own words" style
    assert any(word in texts.lower() for word in ["explain", "what would happen", "how would you verify"])


def test_generate_questions_with_empty_context_uses_generic_templates() -> None:
    """Empty terminal context (no cwd, no panes) falls back to generic templates."""
    ctx = TerminalContext()
    questions = _generate_questions(_shell_track(), _shell_module(), "foundation", 3, ctx)
    texts = " ".join(q.text for q in questions)
    assert "Explain" in texts


# === Defense start with terminal context ===


def test_start_session_with_terminal_context_returns_snapshot() -> None:
    """When terminal_context is provided in the request, the response includes a snapshot."""
    response = client.post(
        START_ENDPOINT,
        json={
            "track_id": "shell",
            "module_id": "shell-basics",
            "terminal_context": {
                "cwd": "/home/learner/shell_03",
                "git_status": "M  sed_transform.sh",
                "panes": {"work": "$ pwd\n/home/learner/shell_03"},
                "git_diff_summary": "",
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["terminal_snapshot"] is not None
    assert data["terminal_snapshot"]["cwd"] == "/home/learner/shell_03"
    assert data["terminal_snapshot"]["panes"]["work"] == "$ pwd\n/home/learner/shell_03"


def test_start_session_with_terminal_context_generates_contextual_questions() -> None:
    """Questions reference the terminal cwd when context is provided."""
    response = client.post(
        START_ENDPOINT,
        json={
            "track_id": "shell",
            "module_id": "shell-basics",
            "terminal_context": {
                "cwd": "/home/learner/grep_project",
                "panes": {"work": "$ grep -r TODO ."},
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    texts = " ".join(q["text"] for q in data["questions"])
    assert "/home/learner/grep_project" in texts


def test_start_session_without_terminal_context_returns_null_snapshot() -> None:
    """Without terminal context (and no tmux), snapshot is null."""
    response = client.post(
        START_ENDPOINT,
        json={"track_id": "shell", "module_id": "shell-basics"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["terminal_snapshot"] is None


def test_terminal_context_persisted_in_backend(
    _fake_persistence_backend: dict[str, Any],
) -> None:
    """Terminal context is stored in the evidence artifacts for later review."""
    response = client.post(
        START_ENDPOINT,
        json={
            "track_id": "shell",
            "module_id": "shell-basics",
            "learner_id": "learner-1",
            "terminal_context": {
                "cwd": "/home/learner/c_02",
                "git_status": "?? main.c",
                "panes": {"build": "gcc -Wall main.c -o main"},
            },
        },
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    persisted = _fake_persistence_backend["defense_sessions"][session_id]
    state = persisted["evidence_artifacts"][0]
    assert state["terminal_context"] is not None
    assert state["terminal_context"]["cwd"] == "/home/learner/c_02"
    assert state["terminal_context"]["panes"]["build"] == "gcc -Wall main.c -o main"


def test_start_session_questions_remain_socratic_with_context() -> None:
    """Even with terminal context, questions must be Socratic — never reveal answers."""
    response = client.post(
        START_ENDPOINT,
        json={
            "track_id": "shell",
            "module_id": "shell-basics",
            "terminal_context": {
                "cwd": "/home/learner/shell_03",
                "panes": {"work": "$ chmod 755 script.sh"},
            },
        },
    )
    assert response.status_code == 200
    data = response.json()
    for q in data["questions"]:
        text_lower = q["text"].lower()
        assert any(word in text_lower for word in ["explain", "what", "how", "describe", "looking", "based"]), (
            f"Question should be Socratic: {q['text']}"
        )
