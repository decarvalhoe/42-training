from __future__ import annotations

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_event_uses_public_api_events_endpoint_contract() -> None:
    with patch("app.main._emit_event_async", new=AsyncMock(return_value="evt-123")) as mock_emit:
        response = client.post(
            "/api/v1/events",
            json={
                "event_type": "mentor_query",
                "learner_id": "learner-42",
                "track_id": "shell",
                "module_id": "shell-basics",
                "checkpoint_index": 0,
                "source_service": "ai_gateway",
                "payload": {"question": "How do I debug cp?"},
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "recorded", "event_id": "evt-123"}
    mock_emit.assert_awaited_once_with(
        "mentor_query",
        learner_id="learner-42",
        track_id="shell",
        module_id="shell-basics",
        checkpoint_index=0,
        source_service="ai_gateway",
        payload={"question": "How do I debug cp?"},
    )
