from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .db import get_session_factory
from .models import PedagogicalEvent

MENTOR_QUERY_RETENTION = timedelta(days=90)
WATCH_CHECKIN_RETENTION = timedelta(days=90)
CHECKPOINT_RETENTION = timedelta(days=365)
MODULE_RETENTION = timedelta(days=730)
MODULE_EVENT_TYPES = ("module_started", "module_completed", "module_skipped")


@dataclass(slots=True)
class CleanupSummary:
    deleted_mentor_queries: int
    deleted_watch_checkins: int
    deleted_checkpoints: int
    deleted_modules: int

    @property
    def total_deleted(self) -> int:
        return (
            self.deleted_mentor_queries + self.deleted_watch_checkins + self.deleted_checkpoints + self.deleted_modules
        )


async def _delete_before(
    session: AsyncSession,
    *,
    event_types: tuple[str, ...],
    cutoff: datetime,
) -> int:
    stmt = (
        delete(PedagogicalEvent)
        .where(PedagogicalEvent.event_type.in_(event_types), PedagogicalEvent.created_at < cutoff)
        .execution_options(synchronize_session=False)
    )
    result = await session.execute(stmt)
    return int(result.rowcount or 0)  # type: ignore[attr-defined]


async def cleanup_expired_events(
    *,
    now: datetime | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> CleanupSummary:
    current_time = now or datetime.now(UTC)
    factory = session_factory or get_session_factory()

    async with factory() as session:
        deleted_mentor_queries = await _delete_before(
            session,
            event_types=("mentor_query",),
            cutoff=current_time - MENTOR_QUERY_RETENTION,
        )
        deleted_watch_checkins = await _delete_before(
            session,
            event_types=("watch_mentor_checkin",),
            cutoff=current_time - WATCH_CHECKIN_RETENTION,
        )
        deleted_checkpoints = await _delete_before(
            session,
            event_types=("checkpoint_submitted",),
            cutoff=current_time - CHECKPOINT_RETENTION,
        )
        deleted_modules = await _delete_before(
            session,
            event_types=MODULE_EVENT_TYPES,
            cutoff=current_time - MODULE_RETENTION,
        )
        await session.commit()

    return CleanupSummary(
        deleted_mentor_queries=deleted_mentor_queries,
        deleted_watch_checkins=deleted_watch_checkins,
        deleted_checkpoints=deleted_checkpoints,
        deleted_modules=deleted_modules,
    )


async def count_events(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(PedagogicalEvent))
    return int(result.scalar_one())


def main() -> int:
    summary = asyncio.run(cleanup_expired_events())
    print(
        "Deleted pedagogical events:",
        f"mentor_query={summary.deleted_mentor_queries}",
        f"watch_mentor_checkin={summary.deleted_watch_checkins}",
        f"checkpoint_submitted={summary.deleted_checkpoints}",
        f"module_events={summary.deleted_modules}",
        f"total={summary.total_deleted}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
