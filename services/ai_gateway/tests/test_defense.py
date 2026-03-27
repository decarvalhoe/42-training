"""Tests for the oral defense MVP flow (#38).

Tests cover the full lifecycle: start session, answer questions, get results.
Key invariants:
- Questions are Socratic — they never reveal answers
- Scoring rewards explanation depth, not keyword recitation
- The system never provides correct answers in feedback
"""

import pytest
from fastapi.testclient import TestClient

from app.defense import DefenseQuestion, clear_sessions, score_answer
from app.main import app

client = TestClient(app)

START_ENDPOINT = "/api/v1/defense/start"
ANSWER_ENDPOINT = "/api/v1/defense/answer"


@pytest.fixture(autouse=True)
def _clean_sessions():
    """Clear in-memory sessions between tests."""
    clear_sessions()
    yield
    clear_sessions()


def _start_session(track_id: str = "shell", module_id: str = "shell-basics", num_questions: int = 3) -> dict:
    response = client.post(
        START_ENDPOINT,
        json={"track_id": track_id, "module_id": module_id, "num_questions": num_questions},
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


def test_start_session_questions_have_structure() -> None:
    data = _start_session()
    for q in data["questions"]:
        assert "question_id" in q
        assert "text" in q
        assert "skill" in q
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
    assert response.status_code == 400


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


# === Unit tests for scoring ===


def test_score_rewards_explanation() -> None:
    q = DefenseQuestion(id="q-1", text="Explain ls", skill="ls", expected_keywords=["list", "files", "directory"])
    score, _ = score_answer(
        q, "The ls command is used to list files in a directory because it reads directory entries."
    )
    assert score >= 0.5


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
