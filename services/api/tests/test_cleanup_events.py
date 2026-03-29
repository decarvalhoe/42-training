from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.cleanup_events import cleanup_expired_events
from app.db import create_async_db_engine
from app.models import Base, PedagogicalEvent


def test_cleanup_expired_events_deletes_only_records_past_ttl(tmp_path: Path) -> None:
    database_path = tmp_path / "cleanup.db"
    engine = create_async_db_engine(f"sqlite+aiosqlite:///{database_path}")
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    now = datetime(2026, 3, 29, 12, 0, tzinfo=UTC)

    async def scenario() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        async with session_factory() as session:
            session.add_all(
                [
                    PedagogicalEvent(
                        event_type="mentor_query",
                        learner_id="default",
                        source_service="ai_gateway",
                        payload={},
                        created_at=now - timedelta(days=91),
                    ),
                    PedagogicalEvent(
                        event_type="mentor_query",
                        learner_id="default",
                        source_service="ai_gateway",
                        payload={},
                        created_at=now - timedelta(days=30),
                    ),
                    PedagogicalEvent(
                        event_type="checkpoint_submitted",
                        learner_id="default",
                        module_id="shell-basics",
                        checkpoint_index=0,
                        source_service="api",
                        payload={},
                        created_at=now - timedelta(days=366),
                    ),
                    PedagogicalEvent(
                        event_type="checkpoint_submitted",
                        learner_id="default",
                        module_id="shell-basics",
                        checkpoint_index=0,
                        source_service="api",
                        payload={},
                        created_at=now - timedelta(days=100),
                    ),
                    PedagogicalEvent(
                        event_type="module_completed",
                        learner_id="default",
                        track_id="shell",
                        module_id="shell-basics",
                        source_service="api",
                        payload={},
                        created_at=now - timedelta(days=731),
                    ),
                    PedagogicalEvent(
                        event_type="module_skipped",
                        learner_id="default",
                        track_id="shell",
                        module_id="shell-streams",
                        source_service="api",
                        payload={},
                        created_at=now - timedelta(days=100),
                    ),
                    PedagogicalEvent(
                        event_type="defense_started",
                        learner_id="default",
                        track_id="shell",
                        module_id="shell-basics",
                        source_service="ai_gateway",
                        payload={},
                        created_at=now - timedelta(days=800),
                    ),
                ]
            )
            await session.commit()

        summary = await cleanup_expired_events(now=now, session_factory=session_factory)
        assert summary.deleted_mentor_queries == 1
        assert summary.deleted_checkpoints == 1
        assert summary.deleted_modules == 1
        assert summary.total_deleted == 3

        async with session_factory() as session:
            result = await session.execute(
                select(PedagogicalEvent.event_type, PedagogicalEvent.module_id).order_by(PedagogicalEvent.event_type)
            )
            remaining = list(result.all())

        assert remaining == [
            ("checkpoint_submitted", "shell-basics"),
            ("defense_started", "shell-basics"),
            ("mentor_query", None),
            ("module_skipped", "shell-streams"),
        ]

        await engine.dispose()

    asyncio.run(scenario())
