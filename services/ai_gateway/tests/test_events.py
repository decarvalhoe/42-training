from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.events import emit_event


def test_emit_event_forwards_to_public_api_events_endpoint() -> None:
    fake_response = MagicMock()
    fake_response.raise_for_status.return_value = None

    with (
        patch.dict("os.environ", {"AI_GATEWAY_API_BASE_URL": "http://api-service:8000"}, clear=False),
        patch("app.events.httpx.post", return_value=fake_response) as mock_post,
    ):
        emit_event(
            "mentor_query",
            learner_id="learner-42",
            track_id="shell",
            module_id="shell-basics",
            payload={"question": "How do I debug cp?"},
        )

    mock_post.assert_called_once_with(
        "http://api-service:8000/api/v1/events",
        json={
            "event_type": "mentor_query",
            "learner_id": "learner-42",
            "track_id": "shell",
            "module_id": "shell-basics",
            "checkpoint_index": None,
            "source_service": "ai_gateway",
            "payload": {"question": "How do I debug cp?"},
        },
        timeout=0.5,
    )


def test_emit_event_swallows_forwarding_failures() -> None:
    with patch("app.events.httpx.post", side_effect=RuntimeError("boom")):
        emit_event("module_started", learner_id="learner-42")
