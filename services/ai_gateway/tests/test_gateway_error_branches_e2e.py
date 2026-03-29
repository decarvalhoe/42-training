"""E2E coverage for AI gateway error branches."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.defense import clear_sessions, get_session
from app.main import app

client = TestClient(app)

_CURRICULUM = {
    "metadata": {"campus": "42 Lausanne"},
    "tracks": [
        {
            "id": "shell",
            "title": "Shell",
            "modules": [
                {
                    "id": "shell-basics",
                    "title": "Navigation",
                    "skills": ["pwd", "ls"],
                    "objectives": ["Navigate a project tree without losing context."],
                    "exit_criteria": ["Explain when to use `pwd` instead of `ls`."],
                }
            ],
        }
    ],
}


@pytest.fixture(autouse=True)
def _clean_sessions() -> Iterator[None]:
    clear_sessions()
    yield
    clear_sessions()


def test_defense_flow_times_out_late_answer_and_reports_failed_result() -> None:
    start = datetime(2026, 3, 29, 12, 0, 0, tzinfo=UTC)

    with (
        patch("app.main.load_curriculum", return_value=_CURRICULUM),
        patch("app.main.persist_defense_session", return_value={}),
        patch("app.main.load_defense_session", side_effect=get_session),
        patch("app.main.sync_defense_session", return_value={}),
        patch("app.main.persist_review_attempt", return_value=None),
    ):
        with patch("app.defense._utc_now", return_value=start):
            start_response = client.post(
                "/api/v1/defense/start",
                json={
                    "track_id": "shell",
                    "module_id": "shell-basics",
                    "num_questions": 1,
                    "question_time_limit_seconds": 20,
                },
            )

        assert start_response.status_code == 200
        start_data = start_response.json()
        assert datetime.fromisoformat(start_data["current_question_deadline"]) == start + timedelta(seconds=20)

        with patch("app.defense._utc_now", return_value=start + timedelta(seconds=25)):
            answer_response = client.post(
                "/api/v1/defense/answer",
                json={
                    "session_id": start_data["session_id"],
                    "question_id": start_data["active_question_id"],
                    "answer": "pwd shows the current directory so I can confirm where I am before running commands.",
                },
            )

        assert answer_response.status_code == 200
        answer_data = answer_response.json()
        assert answer_data["timed_out"] is True
        assert answer_data["score"] == 0.0
        assert answer_data["elapsed_seconds"] == 25.0
        assert answer_data["questions_remaining"] == 0
        assert answer_data["next_question_id"] is None
        assert answer_data["next_question_deadline"] is None

        result_response = client.get(f"/api/v1/defense/{start_data['session_id']}/result")
        assert result_response.status_code == 200
        result_data = result_response.json()
        assert result_data["passed"] is False
        assert result_data["timed_out_questions"] == 1
        assert "exceeded the timer" in result_data["summary"].lower()
        assert result_data["question_results"][0]["timed_out"] is True
        assert result_data["question_results"][0]["elapsed_seconds"] == 25.0
