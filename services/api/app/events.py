from __future__ import annotations

import asyncio
import logging
from typing import Any

from .db import get_session_factory
from .models import PedagogicalEvent

logger = logging.getLogger(__name__)


async def _emit_event_async(
    event_type: str,
    *,
    learner_id: str | None = None,
    track_id: str | None = None,
    module_id: str | None = None,
    checkpoint_index: int | None = None,
    source_service: str = "api",
    payload: dict[str, Any] | None = None,
) -> str:
    session_factory = get_session_factory()

    async with session_factory() as session:
        event = PedagogicalEvent(
            event_type=event_type,
            learner_id=learner_id,
            track_id=track_id,
            module_id=module_id,
            checkpoint_index=checkpoint_index,
            source_service=source_service,
            payload=payload or {},
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        return event.id


def emit_event(
    event_type: str,
    *,
    learner_id: str | None = None,
    track_id: str | None = None,
    module_id: str | None = None,
    checkpoint_index: int | None = None,
    source_service: str = "api",
    payload: dict[str, Any] | None = None,
) -> str | None:
    """Persist a pedagogical event without breaking the caller on DB failure.

    The current API routes are still synchronous. This helper wraps the async
    DB write so existing endpoints can emit events now, while the application
    continues to function even if the database or migration is not ready yet.
    """

    try:
        return asyncio.run(
            _emit_event_async(
                event_type,
                learner_id=learner_id,
                track_id=track_id,
                module_id=module_id,
                checkpoint_index=checkpoint_index,
                source_service=source_service,
                payload=payload,
            )
        )
    except Exception:
        logger.warning("Pedagogical event emission failed", exc_info=True)
        return None
