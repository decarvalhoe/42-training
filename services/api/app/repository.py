from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from copy import deepcopy
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import select

from .db import get_session_factory
from .models import LearnerProfile, Progression
from .progression_state import canonicalize_progression

DEFAULT_LEARNER_ID = "default"
DEFAULT_TRACK = "shell"
DEFAULT_PHASE = "foundation"


def _find_root() -> Path:
    """Find project root: use DATA_ROOT env var (Docker) or traverse up from __file__."""
    env_root = os.environ.get("DATA_ROOT")
    if env_root:
        return Path(env_root)
    for ancestor in Path(__file__).resolve().parents:
        if (ancestor / "packages" / "curriculum" / "data").exists():
            return ancestor
    return Path("/")


ROOT = _find_root()
CURRICULUM_PATH = ROOT / "packages" / "curriculum" / "data" / "42_lausanne_curriculum.json"


@lru_cache(maxsize=1)
def load_curriculum() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(CURRICULUM_PATH.read_text(encoding="utf-8"))
    return result


def reload_curriculum() -> dict[str, Any]:
    load_curriculum.cache_clear()
    return load_curriculum()


def _run_async(awaitable: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)
    raise RuntimeError("Synchronous repository helpers cannot be called from an active event loop")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _copy_json(data: Any) -> Any:
    return json.loads(json.dumps(data))


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"Unsupported datetime value: {value!r}")


def _default_progression(track: str = DEFAULT_TRACK) -> dict[str, Any]:
    return {"learning_plan": {"active_course": track}, "progress": {}}


def _find_module_context(curriculum: dict[str, Any], module_id: str) -> tuple[str, str] | None:
    for track in curriculum.get("tracks", []):
        track_id = str(track.get("id", DEFAULT_TRACK))
        for module in track.get("modules", []):
            if module.get("id") == module_id:
                return track_id, str(module.get("phase", DEFAULT_PHASE))
    return None


async def _get_default_learner(session: Any) -> LearnerProfile | None:
    learner = await session.get(LearnerProfile, DEFAULT_LEARNER_ID)
    if learner is not None:
        return learner

    result = await session.execute(select(LearnerProfile).where(LearnerProfile.login == DEFAULT_LEARNER_ID))
    return result.scalar_one_or_none()


async def _load_progression_from_db() -> dict[str, Any]:
    async with get_session_factory()() as session:
        learner = await _get_default_learner(session)
        if learner is None:
            return _default_progression()

        result = await session.execute(
            select(Progression).where(Progression.learner_id == learner.id).order_by(Progression.module_id)
        )
        progressions = list(result.scalars())

    base = deepcopy(learner.runtime_state or {})
    if not isinstance(base, dict):
        base = {}

    learning_plan = base.get("learning_plan")
    if not isinstance(learning_plan, dict):
        learning_plan = {}
    learning_plan["active_course"] = learner.track or learning_plan.get("active_course", DEFAULT_TRACK)
    learning_plan["active_module"] = learner.current_module
    base["learning_plan"] = learning_plan

    progress = base.get("progress")
    if not isinstance(progress, dict):
        progress = {}
    base["progress"] = progress

    module_status: dict[str, dict[str, Any]] = {}
    checkpoints: list[dict[str, Any]] = []

    for row in progressions:
        evidence_summary = row.evidence_summary if isinstance(row.evidence_summary, dict) else {}
        entry: dict[str, Any] = {"status": row.status}
        if row.started_at is not None:
            entry["started_at"] = _serialize_datetime(row.started_at)
        if row.completed_at is not None:
            entry["completed_at"] = _serialize_datetime(row.completed_at)
        if row.skipped_at is not None:
            entry["skipped_at"] = _serialize_datetime(row.skipped_at)
        skip_reason = evidence_summary.get("skip_reason")
        if isinstance(skip_reason, str) and skip_reason:
            entry["skip_reason"] = skip_reason
        module_status[row.module_id] = entry

        raw_checkpoints = evidence_summary.get("checkpoints", [])
        if isinstance(raw_checkpoints, list):
            checkpoints.extend(_copy_json(raw_checkpoints))

    base["module_status"] = module_status
    if checkpoints:
        checkpoints.sort(
            key=lambda item: (
                str(item.get("submitted_at", "")),
                str(item.get("module_id", "")),
                int(item.get("checkpoint_index", 0)),
            )
        )
        base["checkpoints"] = checkpoints
    else:
        base.pop("checkpoints", None)

    return base


def load_progression() -> dict[str, Any]:
    result: dict[str, Any] = _run_async(_load_progression_from_db())
    return result


def _extract_runtime_state(data: dict[str, Any]) -> dict[str, Any]:
    runtime_state = deepcopy(data)
    runtime_state.pop("module_status", None)
    runtime_state.pop("checkpoints", None)
    return runtime_state


def _build_progression_rows(data: dict[str, Any], fallback_track: str) -> dict[str, dict[str, Any]]:
    curriculum = load_curriculum()
    raw_statuses = data.get("module_status", {})
    statuses = raw_statuses if isinstance(raw_statuses, dict) else {}

    grouped_checkpoints: dict[str, list[dict[str, Any]]] = defaultdict(list)
    raw_checkpoints = data.get("checkpoints", [])
    if isinstance(raw_checkpoints, list):
        for checkpoint in raw_checkpoints:
            if isinstance(checkpoint, dict):
                module_id = checkpoint.get("module_id")
                if isinstance(module_id, str) and module_id:
                    grouped_checkpoints[module_id].append(_copy_json(checkpoint))

    desired_module_ids = set(statuses.keys()) | set(grouped_checkpoints.keys())
    rows: dict[str, dict[str, Any]] = {}

    for module_id in desired_module_ids:
        status_entry = statuses.get(module_id, {})
        if not isinstance(status_entry, dict):
            status_entry = {}

        context = _find_module_context(curriculum, module_id)
        track_id, phase = context if context is not None else (fallback_track, DEFAULT_PHASE)
        evidence_summary: dict[str, Any] = {}
        skip_reason = status_entry.get("skip_reason")
        if isinstance(skip_reason, str) and skip_reason:
            evidence_summary["skip_reason"] = skip_reason
        checkpoints = grouped_checkpoints.get(module_id, [])
        if checkpoints:
            evidence_summary["checkpoints"] = checkpoints

        rows[module_id] = {
            "track_id": track_id,
            "phase": phase,
            "status": str(status_entry.get("status", "not_started")),
            "started_at": _parse_datetime(status_entry.get("started_at")),
            "completed_at": _parse_datetime(status_entry.get("completed_at")),
            "skipped_at": _parse_datetime(status_entry.get("skipped_at")),
            "evidence_summary": evidence_summary,
        }

    return rows


async def _write_progression_to_db(data: dict[str, Any]) -> None:
    payload = canonicalize_progression(deepcopy(data))
    learning_plan = payload.get("learning_plan", {})
    if not isinstance(learning_plan, dict):
        learning_plan = {}

    requested_track = learning_plan.get("active_course")
    track = str(requested_track) if isinstance(requested_track, str) and requested_track else DEFAULT_TRACK
    current_module = learning_plan.get("active_module")
    desired_rows = _build_progression_rows(payload, track)
    runtime_state = _extract_runtime_state(payload)

    async with get_session_factory()() as session:
        learner = await _get_default_learner(session)
        if learner is None:
            learner = LearnerProfile(
                id=DEFAULT_LEARNER_ID,
                login=DEFAULT_LEARNER_ID,
                track=track,
                current_module=str(current_module) if isinstance(current_module, str) else None,
                runtime_state=runtime_state,
                started_at=_utcnow(),
                updated_at=_utcnow(),
            )
            session.add(learner)
            await session.flush()
        else:
            learner.track = track
            learner.current_module = str(current_module) if isinstance(current_module, str) else None
            learner.runtime_state = runtime_state

        result = await session.execute(select(Progression).where(Progression.learner_id == learner.id))
        existing_by_module = {row.module_id: row for row in result.scalars()}

        for module_id, row_data in desired_rows.items():
            row = existing_by_module.pop(module_id, None)
            if row is None:
                row = Progression(
                    learner_id=learner.id,
                    module_id=module_id,
                    track_id=str(row_data["track_id"]),
                    phase=str(row_data["phase"]),
                    status=str(row_data["status"]),
                    started_at=row_data["started_at"],
                    completed_at=row_data["completed_at"],
                    skipped_at=row_data["skipped_at"],
                    evidence_summary=_copy_json(row_data["evidence_summary"]),
                )
                session.add(row)
                continue

            row.track_id = str(row_data["track_id"])
            row.phase = str(row_data["phase"])
            row.status = str(row_data["status"])
            row.started_at = row_data["started_at"]
            row.completed_at = row_data["completed_at"]
            row.skipped_at = row_data["skipped_at"]
            row.evidence_summary = _copy_json(row_data["evidence_summary"])

        for stale_row in existing_by_module.values():
            await session.delete(stale_row)

        await session.commit()


def write_progression(data: dict[str, Any]) -> None:
    _run_async(_write_progression_to_db(data))
