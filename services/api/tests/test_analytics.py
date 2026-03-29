from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.analytics import build_analytics_dashboard


_CURRICULUM = {
    "tracks": [
        {
            "id": "shell",
            "modules": [
                {"id": "shell-basics", "title": "Navigation", "phase": "foundation"},
                {"id": "shell-streams", "title": "Pipes", "phase": "foundation"},
            ],
        },
        {
            "id": "c",
            "modules": [
                {"id": "c-basics", "title": "Syntax", "phase": "foundation"},
            ],
        },
    ]
}


def _event(
    event_type: str,
    *,
    learner_id: str = "default",
    module_id: str | None = None,
    created_at: datetime,
    payload: dict | None = None,
):
    return SimpleNamespace(
        event_type=event_type,
        learner_id=learner_id,
        module_id=module_id,
        created_at=created_at,
        payload=payload or {},
    )


def test_build_analytics_dashboard_computes_summary_and_charts() -> None:
    started = datetime(2026, 3, 29, 9, 0, tzinfo=UTC)
    events = [
        _event("module_started", module_id="shell-basics", created_at=started),
        _event("module_completed", module_id="shell-basics", created_at=started + timedelta(minutes=30)),
        _event("module_started", module_id="shell-streams", created_at=started + timedelta(minutes=35)),
        _event("module_completed", module_id="shell-streams", created_at=started + timedelta(minutes=80)),
        _event(
            "checkpoint_submitted",
            module_id="shell-basics",
            created_at=started + timedelta(minutes=10),
            payload={"self_evaluation": "pass"},
        ),
        _event(
            "checkpoint_submitted",
            module_id="shell-streams",
            created_at=started + timedelta(minutes=60),
            payload={"self_evaluation": "fail"},
        ),
        _event("mentor_query", module_id="shell-basics", created_at=started + timedelta(minutes=5)),
        _event("defense_started", module_id="shell-streams", created_at=started + timedelta(minutes=90)),
    ]

    data = build_analytics_dashboard(_CURRICULUM, events)

    assert data.summary.total_events == 8
    assert data.summary.module_completions == 2
    assert data.summary.average_completion_minutes == 37.5
    assert data.summary.checkpoint_success_rate == 50.0
    assert data.summary.mentor_queries == 1
    assert data.summary.defenses_started == 1

    assert [row.module_id for row in data.modules_completed] == ["shell-basics", "shell-streams"]
    assert data.average_time[0].module_id == "shell-streams"
    assert data.average_time[0].value == 45.0
    assert data.success_rate[0].module_id == "shell-basics"
    assert data.success_rate[0].value == 100.0


def test_build_analytics_dashboard_handles_empty_events() -> None:
    data = build_analytics_dashboard(_CURRICULUM, [])

    assert data.summary.total_events == 0
    assert data.summary.module_completions == 0
    assert data.summary.average_completion_minutes == 0.0
    assert data.summary.checkpoint_success_rate == 0.0
    assert data.modules_completed == []
    assert data.average_time == []
    assert data.success_rate == []
