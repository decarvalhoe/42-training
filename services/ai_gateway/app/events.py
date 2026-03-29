from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_API_BASE_URL = "http://localhost:8000"
PEDAGOGICAL_EVENTS_PATH = "/api/v1/events"


def emit_event(
    event_type: str,
    *,
    learner_id: str | None = "default",
    track_id: str | None = None,
    module_id: str | None = None,
    checkpoint_index: int | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Best-effort pedagogical event forwarding to the API service."""

    api_base_url = os.getenv("AI_GATEWAY_API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
    try:
        response = httpx.post(
            f"{api_base_url}{PEDAGOGICAL_EVENTS_PATH}",
            json={
                "event_type": event_type,
                "learner_id": learner_id,
                "track_id": track_id,
                "module_id": module_id,
                "checkpoint_index": checkpoint_index,
                "source_service": "ai_gateway",
                "payload": payload or {},
            },
            timeout=0.5,
        )
        response.raise_for_status()
    except Exception:
        logger.warning("Pedagogical event forwarding failed", exc_info=True)
