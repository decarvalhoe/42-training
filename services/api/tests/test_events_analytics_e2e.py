from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.events as events_module
from app.db import get_db_session
from app.events import emit_event
from app.main import app
from app.models import Base, PedagogicalEvent

_CURRICULUM = {
    "metadata": {"campus": "42 Lausanne"},
    "tracks": [
        {
            "id": "shell",
            "title": "Shell 0 to Hero",
            "modules": [
                {"id": "shell-basics", "title": "Navigation", "phase": "foundation"},
                {"id": "shell-streams", "title": "Pipes", "phase": "foundation"},
            ],
        }
    ],
}


@pytest.fixture
def analytics_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[TestClient, async_sessionmaker[AsyncSession]]]:
    database_path = tmp_path / "events-analytics.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path}", connect_args={"check_same_thread": False})
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def init_models() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose_engine() -> None:
        await engine.dispose()

    async def override_get_db_session():
        async with session_factory() as session:
            yield session

    asyncio.run(init_models())
    app.dependency_overrides[get_db_session] = override_get_db_session
    monkeypatch.setattr(events_module, "get_session_factory", lambda: session_factory)

    try:
        with TestClient(app) as client:
            yield client, session_factory
    finally:
        app.dependency_overrides.clear()
        asyncio.run(dispose_engine())


async def _fetch_events(session_factory: async_sessionmaker[AsyncSession]) -> list[PedagogicalEvent]:
    async with session_factory() as session:
        result = await session.execute(select(PedagogicalEvent).order_by(PedagogicalEvent.created_at))
        return list(result.scalars().all())


async def _set_created_at(
    session_factory: async_sessionmaker[AsyncSession],
    event_id: str,
    created_at: datetime,
) -> None:
    async with session_factory() as session:
        result = await session.execute(select(PedagogicalEvent).where(PedagogicalEvent.id == event_id))
        event = result.scalar_one()
        event.created_at = created_at
        await session.commit()


def test_emit_event_helper_persists_to_table_and_feeds_analytics_dashboard(
    analytics_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = analytics_client
    started_at = datetime(2026, 3, 29, 9, 0, tzinfo=UTC)

    with patch("app.main.load_curriculum", return_value=_CURRICULUM):
        start_id = emit_event("module_started", learner_id="learner-1", track_id="shell", module_id="shell-basics")
        complete_id = emit_event("module_completed", learner_id="learner-1", track_id="shell", module_id="shell-basics")
        checkpoint_id = emit_event(
            "checkpoint_submitted",
            learner_id="learner-1",
            track_id="shell",
            module_id="shell-basics",
            checkpoint_index=0,
            payload={"self_evaluation": "pass"},
        )
        mentor_id = emit_event("mentor_query", learner_id="learner-1", track_id="shell", module_id="shell-basics")

        assert start_id is not None
        assert complete_id is not None
        assert checkpoint_id is not None
        assert mentor_id is not None

        asyncio.run(_set_created_at(session_factory, start_id, started_at))
        asyncio.run(_set_created_at(session_factory, complete_id, started_at + timedelta(minutes=30)))
        asyncio.run(_set_created_at(session_factory, checkpoint_id, started_at + timedelta(minutes=10)))
        asyncio.run(_set_created_at(session_factory, mentor_id, started_at + timedelta(minutes=5)))

        stored_events = asyncio.run(_fetch_events(session_factory))
        assert len(stored_events) == 4
        assert {event.event_type for event in stored_events} == {
            "module_started",
            "module_completed",
            "checkpoint_submitted",
            "mentor_query",
        }

        response = client.get("/api/v1/analytics/dashboard")

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == {
        "total_events": 4,
        "module_completions": 1,
        "average_completion_minutes": 30.0,
        "checkpoint_success_rate": 100.0,
        "mentor_queries": 1,
        "defenses_started": 0,
        "watch_mentor_checkins": 0,
    }
    assert data["modules_completed"][0]["module_id"] == "shell-basics"
    assert data["average_time"][0]["value"] == 30.0
    assert data["success_rate"][0]["value"] == 100.0


def test_public_events_endpoint_writes_events_that_dashboard_aggregates(
    analytics_client: tuple[TestClient, async_sessionmaker[AsyncSession]],
) -> None:
    client, session_factory = analytics_client
    started_at = datetime(2026, 3, 29, 10, 0, tzinfo=UTC)

    with patch("app.main.load_curriculum", return_value=_CURRICULUM):
        responses = [
            client.post(
                "/api/v1/events",
                json={
                    "event_type": "module_started",
                    "learner_id": "learner-2",
                    "track_id": "shell",
                    "module_id": "shell-streams",
                    "source_service": "api",
                    "payload": {},
                },
            ),
            client.post(
                "/api/v1/events",
                json={
                    "event_type": "module_completed",
                    "learner_id": "learner-2",
                    "track_id": "shell",
                    "module_id": "shell-streams",
                    "source_service": "ai_gateway",
                    "payload": {},
                },
            ),
            client.post(
                "/api/v1/events",
                json={
                    "event_type": "checkpoint_submitted",
                    "learner_id": "learner-2",
                    "track_id": "shell",
                    "module_id": "shell-streams",
                    "checkpoint_index": 1,
                    "source_service": "ai_gateway",
                    "payload": {"self_evaluation": "fail"},
                },
            ),
            client.post(
                "/api/v1/events",
                json={
                    "event_type": "defense_started",
                    "learner_id": "learner-2",
                    "track_id": "shell",
                    "module_id": "shell-streams",
                    "source_service": "ai_gateway",
                    "payload": {},
                },
            ),
        ]

        for response in responses:
            assert response.status_code == 200
            assert response.json()["status"] == "recorded"

        event_ids = [response.json()["event_id"] for response in responses]
        for offset, event_id in enumerate(event_ids):
            asyncio.run(_set_created_at(session_factory, event_id, started_at + timedelta(minutes=offset * 15)))

        stored_events = asyncio.run(_fetch_events(session_factory))
        assert len(stored_events) == 4
        assert {event.source_service for event in stored_events} == {"api", "ai_gateway"}

        dashboard = client.get("/api/v1/analytics/dashboard")

    assert dashboard.status_code == 200
    data = dashboard.json()
    assert data["summary"] == {
        "total_events": 4,
        "module_completions": 1,
        "average_completion_minutes": 15.0,
        "checkpoint_success_rate": 0.0,
        "mentor_queries": 0,
        "defenses_started": 1,
        "watch_mentor_checkins": 0,
    }
    assert data["modules_completed"][0]["module_id"] == "shell-streams"
    assert data["average_time"][0]["module_id"] == "shell-streams"
    assert data["average_time"][0]["value"] == 15.0
    assert data["success_rate"][0]["count"] == 1
