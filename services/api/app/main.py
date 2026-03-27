from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from .repository import load_curriculum, load_progression, write_progression
from .schemas import (
    CheckpointListResponse,
    CheckpointRecord,
    CheckpointSubmission,
    DashboardResponse,
    HealthResponse,
    MetaResponse,
    ModuleCompleteRequest,
    ModuleProgressionResponse,
    ModuleSkipRequest,
    ModuleStartRequest,
    ModuleStatusResponse,
    ProgressionResponse,
    ProgressUpdate,
    TrackDetail,
    TrackSummary,
)
from .validation import find_module, validate_module_activation

app = FastAPI(title="42-training API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api")


# ---------------------------------------------------------------------------
# Global metadata
# ---------------------------------------------------------------------------


@app.get("/api/v1/meta")
def meta() -> MetaResponse:
    curriculum = load_curriculum()
    progression = load_progression()
    return MetaResponse(
        app="42-training",
        campus=curriculum["metadata"]["campus"],
        active_course=progression.get("learning_plan", {}).get("active_course", "shell"),
        pace_mode=progression.get("learning_plan", {}).get("pace_mode", "self_paced"),
    )


# ---------------------------------------------------------------------------
# Curriculum (read-only)
# ---------------------------------------------------------------------------


@app.get("/api/v1/curriculum/dashboard")
def curriculum_dashboard() -> DashboardResponse:
    return DashboardResponse(
        curriculum=load_curriculum(),
        progression=load_progression(),
    )


@app.get("/api/v1/curriculum/tracks")
def curriculum_tracks() -> list[TrackSummary]:
    curriculum = load_curriculum()
    result: list[TrackSummary] = []
    for track in curriculum["tracks"]:
        result.append(
            TrackSummary(
                id=track["id"],
                title=track["title"],
                summary=track["summary"],
                why_it_matters=track["why_it_matters"],
                module_count=len(track.get("modules", [])),
            )
        )
    return result


@app.get("/api/v1/curriculum/tracks/{track_id}")
def curriculum_track_detail(track_id: str) -> TrackDetail:
    curriculum = load_curriculum()
    for track in curriculum["tracks"]:
        if track["id"] == track_id:
            return TrackDetail(**track)
    raise HTTPException(status_code=404, detail="Track not found")


# ---------------------------------------------------------------------------
# Progression (read + mutations)
# ---------------------------------------------------------------------------


@app.get("/api/v1/progression")
def progression() -> ProgressionResponse:
    return ProgressionResponse(**load_progression())


@app.post("/api/v1/progression")
def update_progression(payload: ProgressUpdate) -> ProgressionResponse:
    current = load_progression()
    learning_plan = current.setdefault("learning_plan", {})
    progress = current.setdefault("progress", {})

    updates = payload.model_dump(exclude_none=True)

    for key in ("active_course", "active_module", "pace_mode"):
        if key in updates:
            learning_plan[key] = updates[key]

    for key in ("current_exercise", "current_step"):
        if key in updates:
            progress[key] = updates[key]

    if "next_command" in updates:
        current["next_command"] = updates["next_command"]

    # Validate active_module change against business rules
    if "active_module" in updates:
        target_module = updates["active_module"]
        curriculum = load_curriculum()
        completed = set(progress.get("completed_modules", []))
        errors = validate_module_activation(curriculum, current, target_module, completed)
        if errors:
            raise HTTPException(status_code=422, detail={"validation_errors": errors})

    write_progression(current)
    return ProgressionResponse(**current)


# --- Helpers for module progression ---


def _find_module(module_id: str) -> tuple[dict[str, object], dict[str, object]]:
    """Return (track, module) for a given module_id, or raise 404."""
    curriculum = load_curriculum()
    for track in curriculum["tracks"]:
        for module in track.get("modules", []):
            if module["id"] == module_id:
                return track, module
    raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")


def _get_module_statuses(progression: dict[str, object]) -> dict[str, dict[str, object]]:
    """Return the module_status dict from progression, creating it if absent."""
    return progression.setdefault("module_status", {})  # type: ignore[return-value]


def _check_prerequisites(module_id: str, track: dict[str, object], progression: dict[str, object]) -> list[str]:
    """Return list of prerequisite module IDs that are not completed/skipped."""
    modules: list[dict[str, object]] = track.get("modules", [])  # type: ignore[assignment]
    module_ids: list[str] = [str(m["id"]) for m in modules]
    if module_id not in module_ids:
        return []
    idx = module_ids.index(module_id)
    if idx == 0:
        return []
    statuses = _get_module_statuses(progression)
    missing: list[str] = []
    for prev_id in module_ids[:idx]:
        prev_status = statuses.get(prev_id, {})
        if isinstance(prev_status, dict) and prev_status.get("status") in ("completed", "skipped"):
            continue
        missing.append(prev_id)
    return missing


# --- Module progression endpoints (Issue #24) ---


@app.get("/api/v1/modules/{module_id}/status")
def module_status(module_id: str) -> ModuleStatusResponse:
    track, _module = _find_module(module_id)
    progression_data = load_progression()
    statuses = _get_module_statuses(progression_data)
    entry = statuses.get(module_id, {})
    if not isinstance(entry, dict):
        entry = {}
    return ModuleStatusResponse(
        module_id=module_id,
        track_id=track["id"],  # type: ignore[arg-type]
        status=entry.get("status", "not_started"),  # type: ignore[arg-type]
        started_at=entry.get("started_at"),  # type: ignore[arg-type]
        completed_at=entry.get("completed_at"),  # type: ignore[arg-type]
        skipped_at=entry.get("skipped_at"),  # type: ignore[arg-type]
        skip_reason=entry.get("skip_reason"),  # type: ignore[arg-type]
    )


@app.post("/api/v1/modules/{module_id}/start")
def module_start(module_id: str, payload: ModuleStartRequest | None = None) -> ModuleProgressionResponse:
    track, _module = _find_module(module_id)
    progression_data = load_progression()

    missing = _check_prerequisites(module_id, track, progression_data)
    if missing:
        raise HTTPException(
            status_code=409,
            detail={
                "module_id": module_id,
                "missing_prerequisites": missing,
                "message": f"Prerequisites not met: {', '.join(missing)}",
            },
        )

    statuses = _get_module_statuses(progression_data)
    current = statuses.get(module_id, {})
    if isinstance(current, dict) and current.get("status") == "in_progress":
        return ModuleProgressionResponse(
            module_id=module_id,
            track_id=track["id"],  # type: ignore[arg-type]
            status="in_progress",
            message="Module already in progress",
        )

    now = datetime.now(UTC).isoformat()
    statuses[module_id] = {"status": "in_progress", "started_at": now}
    write_progression(progression_data)

    return ModuleProgressionResponse(
        module_id=module_id,
        track_id=track["id"],  # type: ignore[arg-type]
        status="in_progress",
        message="Module started",
    )


@app.post("/api/v1/modules/{module_id}/complete")
def module_complete(module_id: str, payload: ModuleCompleteRequest | None = None) -> ModuleProgressionResponse:
    track, _module = _find_module(module_id)
    progression_data = load_progression()
    statuses = _get_module_statuses(progression_data)
    current = statuses.get(module_id, {})

    if not isinstance(current, dict) or current.get("status") != "in_progress":
        raise HTTPException(
            status_code=409,
            detail=f"Module '{module_id}' must be in_progress to complete (current: {current.get('status', 'not_started') if isinstance(current, dict) else 'not_started'})",
        )

    now = datetime.now(UTC).isoformat()
    current["status"] = "completed"
    current["completed_at"] = now
    statuses[module_id] = current
    write_progression(progression_data)

    return ModuleProgressionResponse(
        module_id=module_id,
        track_id=track["id"],  # type: ignore[arg-type]
        status="completed",
        message="Module completed",
    )


@app.post("/api/v1/modules/{module_id}/skip")
def module_skip(module_id: str, payload: ModuleSkipRequest | None = None) -> ModuleProgressionResponse:
    track, _module = _find_module(module_id)
    progression_data = load_progression()
    statuses = _get_module_statuses(progression_data)

    now = datetime.now(UTC).isoformat()
    entry: dict[str, object] = {"status": "skipped", "skipped_at": now}
    if payload and payload.reason:
        entry["skip_reason"] = payload.reason
    statuses[module_id] = entry
    write_progression(progression_data)

    return ModuleProgressionResponse(
        module_id=module_id,
        track_id=track["id"],  # type: ignore[arg-type]
        status="skipped",
        message="Module skipped",
    )


# --- Module validation endpoint (Issue #26) ---


@app.post("/api/v1/modules/{module_id}/validate")
def validate_module(module_id: str) -> dict[str, object]:
    """Dry-run validation: check if a module can be activated."""
    curriculum = load_curriculum()
    if find_module(curriculum, module_id) is None:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")
    progression_data = load_progression()
    completed = set(progression_data.get("progress", {}).get("completed_modules", []))
    errors = validate_module_activation(curriculum, progression_data, module_id, completed)
    return {
        "module_id": module_id,
        "valid": len(errors) == 0,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Backward-compatible redirects (old -> new canonical routes)
# ---------------------------------------------------------------------------


@app.get("/api/v1/dashboard")
def legacy_dashboard() -> RedirectResponse:
    return RedirectResponse(url="/api/v1/curriculum/dashboard", status_code=301)


@app.get("/api/v1/tracks")
def legacy_tracks() -> RedirectResponse:
    return RedirectResponse(url="/api/v1/curriculum/tracks", status_code=301)


@app.get("/api/v1/tracks/{track_id}")
def legacy_track_detail(track_id: str) -> RedirectResponse:
    return RedirectResponse(url=f"/api/v1/curriculum/tracks/{track_id}", status_code=301)


# ---------------------------------------------------------------------------
# Checkpoint submission (Issue #37)
# ---------------------------------------------------------------------------


def _find_module_in_curriculum(module_id: str) -> dict[str, object] | None:
    """Return the module dict from curriculum, or None."""
    curriculum = load_curriculum()
    for track in curriculum.get("tracks", []):
        for module in track.get("modules", []):
            if module["id"] == module_id:
                return dict(module)
    return None


@app.post("/api/v1/checkpoints/submit")
def submit_checkpoint(payload: CheckpointSubmission) -> CheckpointRecord:
    module = _find_module_in_curriculum(payload.module_id)
    if module is None:
        raise HTTPException(status_code=404, detail=f"Module '{payload.module_id}' not found")

    exit_criteria = cast(list[str], module.get("exit_criteria", []))
    if payload.checkpoint_index >= len(exit_criteria):
        raise HTTPException(
            status_code=422,
            detail=f"checkpoint_index {payload.checkpoint_index} out of range (module has {len(exit_criteria)} exit criteria)",
        )

    prompt = exit_criteria[payload.checkpoint_index]
    now = datetime.now(UTC).isoformat()

    record = CheckpointRecord(
        module_id=payload.module_id,
        checkpoint_index=payload.checkpoint_index,
        type=payload.type,
        prompt=prompt,
        evidence=payload.evidence,
        self_evaluation=payload.self_evaluation,
        submitted_at=now,
    )

    # Persist to progression.json under checkpoints key
    progression_data = load_progression()
    checkpoints = progression_data.setdefault("checkpoints", [])
    checkpoints.append(record.model_dump())
    write_progression(progression_data)

    return record


@app.get("/api/v1/checkpoints/{module_id}")
def list_checkpoints(module_id: str) -> CheckpointListResponse:
    module = _find_module_in_curriculum(module_id)
    if module is None:
        raise HTTPException(status_code=404, detail=f"Module '{module_id}' not found")

    exit_criteria = cast(list[str], module.get("exit_criteria", []))
    progression_data = load_progression()
    submissions = progression_data.get("checkpoints", [])

    # Build checkpoint list with submission status
    result: list[dict[str, object]] = []
    for idx, criterion in enumerate(exit_criteria):
        matching = [s for s in submissions if s.get("module_id") == module_id and s.get("checkpoint_index") == idx]
        latest = matching[-1] if matching else None
        result.append(
            {
                "index": idx,
                "prompt": criterion,
                "submitted": latest is not None,
                "self_evaluation": latest["self_evaluation"] if latest else None,
                "submitted_at": latest["submitted_at"] if latest else None,
            }
        )

    return CheckpointListResponse(module_id=module_id, checkpoints=result)
