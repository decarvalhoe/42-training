from __future__ import annotations

from collections import Counter, defaultdict, deque
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import PedagogicalEvent
from .schemas import AnalyticsDashboardResponse


async def fetch_pedagogical_events(db: AsyncSession) -> list[PedagogicalEvent]:
    result = await db.execute(select(PedagogicalEvent).order_by(PedagogicalEvent.created_at))
    return list(result.scalars().all())


def _parse_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _module_lookup(curriculum: dict[str, Any]) -> dict[str, dict[str, str]]:
    lookup: dict[str, dict[str, str]] = {}
    for track in curriculum.get("tracks", []):
        track_id = str(track.get("id", ""))
        for module in track.get("modules", []):
            module_id = str(module.get("id", ""))
            lookup[module_id] = {
                "track_id": track_id,
                "module_title": str(module.get("title", module_id)),
                "phase": str(module.get("phase", "unknown")),
            }
    return lookup


def _chart_rows(
    values: dict[str, float] | Counter[str],
    curriculum: dict[str, Any],
    *,
    count_lookup: dict[str, int] | None = None,
    suffix: str = "",
) -> list[dict[str, object]]:
    modules = _module_lookup(curriculum)
    rows: list[dict[str, object]] = []
    for module_id, value in values.items():
        module_meta = modules.get(module_id, {})
        rows.append(
            {
                "module_id": module_id,
                "module_title": module_meta.get("module_title", module_id),
                "track_id": module_meta.get("track_id", "unknown"),
                "phase": module_meta.get("phase", "unknown"),
                "value": round(float(value), 1),
                "count": count_lookup.get(module_id) if count_lookup else int(value),
                "suffix": suffix,
            }
        )
    rows.sort(key=lambda row: float(row["value"]), reverse=True)  # type: ignore[arg-type]
    return rows


def build_analytics_dashboard(
    curriculum: dict[str, Any],
    events: list[PedagogicalEvent] | list[Any],
) -> AnalyticsDashboardResponse:
    if not events:
        return AnalyticsDashboardResponse(
            summary={  # type: ignore[arg-type]
                "total_events": 0,
                "module_completions": 0,
                "average_completion_minutes": 0.0,
                "checkpoint_success_rate": 0.0,
                "mentor_queries": 0,
                "defenses_started": 0,
            },
            modules_completed=[],
            average_time=[],
            success_rate=[],
        )

    completion_counts: Counter[str] = Counter()
    checkpoint_totals: Counter[str] = Counter()
    checkpoint_passes: Counter[str] = Counter()
    mentor_queries = 0
    defenses_started = 0

    durations_by_module: dict[str, list[float]] = defaultdict(list)
    starts_by_key: dict[tuple[str, str], deque[datetime]] = defaultdict(deque)

    sorted_events = sorted(
        events,
        key=lambda event: _parse_datetime(getattr(event, "created_at", None)) or datetime.min,
    )

    for event in sorted_events:
        event_type = getattr(event, "event_type", "")
        learner_id = str(getattr(event, "learner_id", None) or "default")
        module_id = str(getattr(event, "module_id", None) or "")
        created_at = _parse_datetime(getattr(event, "created_at", None))
        payload = getattr(event, "payload", {}) or {}

        if event_type == "module_started" and module_id and created_at is not None:
            starts_by_key[(learner_id, module_id)].append(created_at)
            continue

        if event_type == "module_completed" and module_id:
            completion_counts[module_id] += 1
            if created_at is not None and starts_by_key[(learner_id, module_id)]:
                started_at = starts_by_key[(learner_id, module_id)].popleft()
                duration_minutes = (created_at - started_at).total_seconds() / 60
                if duration_minutes >= 0:
                    durations_by_module[module_id].append(duration_minutes)
            continue

        if event_type == "checkpoint_submitted" and module_id:
            checkpoint_totals[module_id] += 1
            if payload.get("self_evaluation") == "pass":
                checkpoint_passes[module_id] += 1
            continue

        if event_type == "mentor_query":
            mentor_queries += 1
            continue

        if event_type == "defense_started":
            defenses_started += 1
            continue

    average_time_by_module = {
        module_id: (sum(durations) / len(durations))
        for module_id, durations in durations_by_module.items()
        if durations
    }
    success_rate_by_module = {
        module_id: (checkpoint_passes[module_id] / total) * 100
        for module_id, total in checkpoint_totals.items()
        if total > 0
    }

    total_durations = [duration for durations in durations_by_module.values() for duration in durations]
    overall_average_minutes = (sum(total_durations) / len(total_durations)) if total_durations else 0.0
    overall_success_rate = (
        (sum(checkpoint_passes.values()) / sum(checkpoint_totals.values())) * 100 if checkpoint_totals else 0.0
    )

    return AnalyticsDashboardResponse(
        summary={  # type: ignore[arg-type]
            "total_events": len(events),
            "module_completions": sum(completion_counts.values()),
            "average_completion_minutes": round(overall_average_minutes, 1),
            "checkpoint_success_rate": round(overall_success_rate, 1),
            "mentor_queries": mentor_queries,
            "defenses_started": defenses_started,
        },
        modules_completed=_chart_rows(completion_counts, curriculum, suffix=" completions"),  # type: ignore[arg-type]
        average_time=_chart_rows(average_time_by_module, curriculum, suffix=" min"),  # type: ignore[arg-type]
        success_rate=_chart_rows(success_rate_by_module, curriculum, count_lookup=checkpoint_totals, suffix="%"),  # type: ignore[arg-type]
    )
