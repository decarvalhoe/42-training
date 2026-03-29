"""Reliability tests for analytics event ingestion.

Covers:
- DB error handling (graceful degradation in sync wrapper)
- Idempotence (duplicate payloads produce distinct events)
- Concurrent ingestion (parallel writes don't corrupt)
- Endpoint-level error surfacing (DB failure on POST /api/v1/events)
- Partial failure isolation (one bad event doesn't block others)
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.events as events_module
from app.db import get_db_session
from app.events import _emit_event_async, emit_event
from app.main import app
from app.models import Base, PedagogicalEvent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reliability_db(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, async_sessionmaker[AsyncSession]]]:
    """Spin up a throwaway SQLite DB wired into the app and event helpers."""
    database_path = tmp_path / "reliability.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path}",
        connect_args={"check_same_thread": False},
    )
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    asyncio.run(_create_tables(engine))
    monkeypatch.setattr(events_module, "get_session_factory", lambda: session_factory)

    async def override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        with TestClient(app) as client:
            yield client, session_factory
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


async def _create_tables(engine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _count_events(sf: async_sessionmaker[AsyncSession]) -> int:
    async with sf() as session:
        result = await session.execute(select(PedagogicalEvent))
        return len(list(result.scalars().all()))


async def _fetch_event_ids(sf: async_sessionmaker[AsyncSession]) -> list[str]:
    async with sf() as session:
        result = await session.execute(select(PedagogicalEvent.id).order_by(PedagogicalEvent.created_at))
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# 1. DB error handling — sync emit_event wrapper
# ---------------------------------------------------------------------------


class TestEmitEventGracefulDegradation:
    """The sync emit_event() wrapper must never propagate DB exceptions."""

    def test_returns_none_on_db_failure(self) -> None:
        with patch.object(events_module, "get_session_factory", side_effect=RuntimeError("connection refused")):
            result = emit_event("module_started", learner_id="learner-1", track_id="shell")

        assert result is None

    def test_returns_none_on_commit_failure(self) -> None:
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock(side_effect=RuntimeError("disk full"))
        mock_session.add = lambda x: None
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = lambda: mock_session  # noqa: E731
        with patch.object(events_module, "get_session_factory", return_value=mock_factory):
            result = emit_event("module_started", learner_id="learner-1")

        assert result is None

    def test_does_not_raise_on_unexpected_exception(self) -> None:
        with patch.object(events_module, "get_session_factory", side_effect=TypeError("weird")):
            # Must not propagate — caller should keep running.
            result = emit_event("checkpoint_submitted", learner_id="learner-1")

        assert result is None


# ---------------------------------------------------------------------------
# 2. Async _emit_event_async — propagates errors
# ---------------------------------------------------------------------------


class TestEmitEventAsyncPropagation:
    """Unlike the sync wrapper, the async function MUST raise on failure."""

    @pytest.mark.asyncio
    async def test_raises_on_session_factory_error(self) -> None:
        with patch.object(events_module, "get_session_factory", side_effect=RuntimeError("no DB")):
            with pytest.raises(RuntimeError, match="no DB"):
                await _emit_event_async("module_started", learner_id="learner-1")


# ---------------------------------------------------------------------------
# 3. Idempotence — duplicate payloads create distinct events
# ---------------------------------------------------------------------------


class TestIdempotence:
    """Each call generates a unique event ID even with identical payloads."""

    def test_duplicate_payloads_produce_distinct_ids(
        self,
        reliability_db: tuple[TestClient, async_sessionmaker[AsyncSession]],
    ) -> None:
        _client, session_factory = reliability_db
        payload = dict(
            event_type="module_started",
            learner_id="learner-dup",
            track_id="shell",
            module_id="shell-basics",
            source_service="api",
            payload={},
        )

        id_1 = asyncio.run(_emit_event_async(**payload))
        id_2 = asyncio.run(_emit_event_async(**payload))

        assert id_1 != id_2
        assert asyncio.run(_count_events(session_factory)) == 2

    def test_duplicate_http_posts_produce_distinct_events(
        self,
        reliability_db: tuple[TestClient, async_sessionmaker[AsyncSession]],
    ) -> None:
        client, session_factory = reliability_db
        body = {
            "event_type": "mentor_query",
            "learner_id": "learner-dup",
            "track_id": "shell",
            "module_id": "shell-basics",
            "source_service": "ai_gateway",
            "payload": {"question": "same question"},
        }

        r1 = client.post("/api/v1/events", json=body)
        r2 = client.post("/api/v1/events", json=body)

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["event_id"] != r2.json()["event_id"]
        assert asyncio.run(_count_events(session_factory)) == 2


# ---------------------------------------------------------------------------
# 4. Concurrent ingestion
# ---------------------------------------------------------------------------


class TestConcurrentIngestion:
    """Parallel event writes must all persist without data loss."""

    def test_parallel_writes_all_persist(
        self,
        reliability_db: tuple[TestClient, async_sessionmaker[AsyncSession]],
    ) -> None:
        _client, session_factory = reliability_db
        n_events = 20

        async def fire_all() -> list[str]:
            tasks = [
                _emit_event_async(
                    "checkpoint_submitted",
                    learner_id=f"learner-{i}",
                    track_id="shell",
                    module_id="shell-basics",
                    checkpoint_index=i,
                    payload={"index": i},
                )
                for i in range(n_events)
            ]
            return await asyncio.gather(*tasks)

        ids = asyncio.run(fire_all())
        assert len(ids) == n_events
        assert len(set(ids)) == n_events  # all unique
        assert asyncio.run(_count_events(session_factory)) == n_events


# ---------------------------------------------------------------------------
# 5. Endpoint-level error surfacing
# ---------------------------------------------------------------------------


class TestEndpointErrorHandling:
    """POST /api/v1/events must return 500 when the DB write fails."""

    def test_returns_500_on_db_error(self) -> None:
        client = TestClient(app, raise_server_exceptions=False)
        with patch("app.main._emit_event_async", new=AsyncMock(side_effect=RuntimeError("db down"))):
            response = client.post(
                "/api/v1/events",
                json={
                    "event_type": "module_started",
                    "learner_id": "learner-err",
                    "source_service": "api",
                    "payload": {},
                },
            )
        assert response.status_code == 500

    def test_returns_422_on_invalid_event_type(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/api/v1/events",
            json={
                "event_type": "invalid_event",
                "learner_id": "learner-err",
                "source_service": "api",
                "payload": {},
            },
        )
        assert response.status_code == 422

    def test_returns_422_on_negative_checkpoint_index(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/api/v1/events",
            json={
                "event_type": "checkpoint_submitted",
                "checkpoint_index": -1,
                "source_service": "api",
                "payload": {},
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# 6. Partial failure isolation
# ---------------------------------------------------------------------------


class TestPartialFailureIsolation:
    """A failed event emission must not prevent subsequent events."""

    def test_emit_event_recovers_after_failure(
        self,
        reliability_db: tuple[TestClient, async_sessionmaker[AsyncSession]],
    ) -> None:
        _client, session_factory = reliability_db

        # First call fails
        with patch.object(events_module, "get_session_factory", side_effect=RuntimeError("transient")):
            failed = emit_event("module_started", learner_id="learner-iso")
        assert failed is None

        # Second call succeeds (real DB is back)
        succeeded = emit_event("module_started", learner_id="learner-iso")
        assert succeeded is not None
        assert asyncio.run(_count_events(session_factory)) == 1

    def test_endpoint_recovers_after_transient_failure(
        self,
        reliability_db: tuple[TestClient, async_sessionmaker[AsyncSession]],
    ) -> None:
        client, session_factory = reliability_db
        body = {
            "event_type": "module_started",
            "learner_id": "learner-iso",
            "source_service": "api",
            "payload": {},
        }

        # Simulate transient failure then recovery
        no_raise_client = TestClient(app, raise_server_exceptions=False)
        app.dependency_overrides[get_db_session] = app.dependency_overrides.get(get_db_session, get_db_session)
        with patch("app.main._emit_event_async", new=AsyncMock(side_effect=RuntimeError("transient"))):
            r1 = no_raise_client.post("/api/v1/events", json=body)
        assert r1.status_code == 500

        # Real call succeeds
        r2 = client.post("/api/v1/events", json=body)
        assert r2.status_code == 200
        assert r2.json()["event_id"] is not None
        assert asyncio.run(_count_events(session_factory)) == 1


# ---------------------------------------------------------------------------
# 7. Payload integrity
# ---------------------------------------------------------------------------


class TestPayloadIntegrity:
    """Complex JSON payloads must round-trip through ingestion."""

    def test_nested_payload_persisted_faithfully(
        self,
        reliability_db: tuple[TestClient, async_sessionmaker[AsyncSession]],
    ) -> None:
        _client, session_factory = reliability_db
        complex_payload = {
            "question": "How does malloc work?",
            "context": {"module": "c-memory", "attempt": 3},
            "tags": ["memory", "pointers", "heap"],
            "scores": [0.8, 0.95, 1.0],
        }

        event_id = asyncio.run(
            _emit_event_async(
                "mentor_query",
                learner_id="learner-pay",
                track_id="c",
                module_id="c-memory",
                payload=complex_payload,
            )
        )

        async def fetch_payload() -> dict:
            async with session_factory() as session:
                result = await session.execute(
                    select(PedagogicalEvent).where(PedagogicalEvent.id == event_id)
                )
                return result.scalar_one().payload

        stored = asyncio.run(fetch_payload())
        assert stored == complex_payload

    def test_empty_payload_defaults_to_empty_dict(
        self,
        reliability_db: tuple[TestClient, async_sessionmaker[AsyncSession]],
    ) -> None:
        _client, session_factory = reliability_db

        event_id = asyncio.run(
            _emit_event_async("module_started", learner_id="learner-empty")
        )

        async def fetch_payload() -> dict:
            async with session_factory() as session:
                result = await session.execute(
                    select(PedagogicalEvent).where(PedagogicalEvent.id == event_id)
                )
                return result.scalar_one().payload

        stored = asyncio.run(fetch_payload())
        assert stored == {}
