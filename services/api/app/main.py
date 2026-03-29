from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .analytics import build_analytics_dashboard, fetch_pedagogical_events
from .auth import router as auth_router
from .db import get_db_session
from .evidence import persist_checkpoint_evidence, persist_defense_evidence, persist_review_evidence
from .events import _emit_event_async, emit_event
from .models import DefenseSession as DefenseSessionModel
from .models import ReviewAttempt as ReviewAttemptModel
from .profiles import router as profiles_router
from .progression_state import canonicalize_progression, get_completed_module_ids, get_module_statuses
from .repository import load_curriculum, load_progression, write_progression
from .schemas import (
    AnalyticsDashboardResponse,
    CheckpointListResponse,
    CheckpointRecord,
    CheckpointSubmission,
    DashboardResponse,
    DefenseSessionCreate,
    DefenseSessionRecord,
    HealthResponse,
    MetaResponse,
    ModuleCompleteRequest,
    ModuleProgressionResponse,
    ModuleSkipRequest,
    ModuleStartRequest,
    ModuleStatusResponse,
    PedagogicalEventCreate,
    PedagogicalEventResponse,
    ProgressionResponse,
    ProgressUpdate,
    ReviewAttemptCreate,
    ReviewAttemptRecord,
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

app.include_router(auth_router)
app.include_router(profiles_router)


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


@app.get("/api/v1/analytics/dashboard", response_model=AnalyticsDashboardResponse)
async def analytics_dashboard(db: AsyncSession = Depends(get_db_session)) -> AnalyticsDashboardResponse:
    curriculum = load_curriculum()
    events = await fetch_pedagogical_events(db)
    return build_analytics_dashboard(curriculum, events)


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
    return ProgressionResponse(**canonicalize_progression(load_progression()))


@app.post("/api/v1/progression")
def update_progression(payload: ProgressUpdate) -> ProgressionResponse:
    current = canonicalize_progression(load_progression())
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
        completed = get_completed_module_ids(current)
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


def _check_prerequisites(module_id: str, track: dict[str, object], progression: dict[str, object]) -> list[str]:
    """Return list of prerequisite module IDs that are not completed/skipped."""
    modules: list[dict[str, object]] = track.get("modules", [])  # type: ignore[assignment]
    module_ids: list[str] = [str(m["id"]) for m in modules]
    if module_id not in module_ids:
        return []
    idx = module_ids.index(module_id)
    if idx == 0:
        return []
    statuses = get_module_statuses(progression)
    missing: list[str] = []
    for prev_id in module_ids[:idx]:
        prev_status = statuses.get(prev_id, {})
        if isinstance(prev_status, dict) and prev_status.get("status") in ("completed", "skipped"):
            continue
        missing.append(prev_id)
    return missing


def _serialize_defense_session(defense_session: DefenseSessionModel) -> DefenseSessionRecord:
    return DefenseSessionRecord(
        session_id=defense_session.session_id,
        learner_id=defense_session.learner_id,
        module_id=defense_session.module_id,
        questions=list(defense_session.questions or []),
        answers=list(defense_session.answers or []),
        scores=list(defense_session.scores or []),
        status=defense_session.status,
        evidence_artifacts=list(defense_session.evidence_artifacts or []),
        created_at=defense_session.created_at,
        updated_at=defense_session.updated_at,
    )


def _serialize_review_attempt(review_attempt: ReviewAttemptModel) -> ReviewAttemptRecord:
    return ReviewAttemptRecord(
        id=review_attempt.id,
        learner_id=review_attempt.learner_id,
        reviewer_id=review_attempt.reviewer_id,
        module_id=review_attempt.module_id,
        code_snippet=review_attempt.code_snippet,
        feedback=review_attempt.feedback,
        questions=list(review_attempt.questions or []),
        score=review_attempt.score,
        evidence_artifacts=list(review_attempt.evidence_artifacts or []),
        created_at=review_attempt.created_at,
        updated_at=review_attempt.updated_at,
    )


# --- Module progression endpoints (Issue #24) ---


@app.get("/api/v1/modules/{module_id}/status")
def module_status(module_id: str) -> ModuleStatusResponse:
    track, _module = _find_module(module_id)
    progression_data = canonicalize_progression(load_progression())
    statuses = get_module_statuses(progression_data)
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
    progression_data = canonicalize_progression(load_progression())

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

    statuses = get_module_statuses(progression_data)
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
    emit_event(
        "module_started",
        learner_id=str(payload.learner_id) if payload is not None else "default",
        track_id=str(track["id"]),
        module_id=module_id,
        payload={"status": "in_progress", "started_at": now},
    )

    return ModuleProgressionResponse(
        module_id=module_id,
        track_id=track["id"],  # type: ignore[arg-type]
        status="in_progress",
        message="Module started",
    )


@app.post("/api/v1/modules/{module_id}/complete")
def module_complete(module_id: str, payload: ModuleCompleteRequest | None = None) -> ModuleProgressionResponse:
    track, _module = _find_module(module_id)
    progression_data = canonicalize_progression(load_progression())
    statuses = get_module_statuses(progression_data)
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
    emit_event(
        "module_completed",
        learner_id=str(payload.learner_id) if payload is not None else "default",
        track_id=str(track["id"]),
        module_id=module_id,
        payload={"status": "completed", "completed_at": now},
    )

    return ModuleProgressionResponse(
        module_id=module_id,
        track_id=track["id"],  # type: ignore[arg-type]
        status="completed",
        message="Module completed",
    )


@app.post("/api/v1/modules/{module_id}/skip")
def module_skip(module_id: str, payload: ModuleSkipRequest | None = None) -> ModuleProgressionResponse:
    track, _module = _find_module(module_id)
    progression_data = canonicalize_progression(load_progression())
    statuses = get_module_statuses(progression_data)

    now = datetime.now(UTC).isoformat()
    entry: dict[str, object] = {"status": "skipped", "skipped_at": now}
    if payload and payload.reason:
        entry["skip_reason"] = payload.reason
    statuses[module_id] = entry
    write_progression(progression_data)
    emit_event(
        "module_skipped",
        learner_id=str(payload.learner_id) if payload is not None else "default",
        track_id=str(track["id"]),
        module_id=module_id,
        payload=dict(entry),
    )

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
    progression_data = canonicalize_progression(load_progression())
    completed = get_completed_module_ids(progression_data)
    errors = validate_module_activation(curriculum, progression_data, module_id, completed)
    return {
        "module_id": module_id,
        "valid": len(errors) == 0,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Defense sessions and review attempts persistence (Issue #128)
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/defense-sessions",
    response_model=DefenseSessionRecord,
    status_code=status.HTTP_201_CREATED,
)
async def create_defense_session(
    payload: DefenseSessionCreate,
    db: AsyncSession = Depends(get_db_session),
) -> DefenseSessionRecord:
    existing = await db.execute(select(DefenseSessionModel).where(DefenseSessionModel.session_id == payload.session_id))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Defense session already exists")

    defense_session = DefenseSessionModel(
        session_id=payload.session_id,
        learner_id=payload.learner_id,
        module_id=payload.module_id,
        questions=payload.questions,
        answers=payload.answers,
        scores=payload.scores,
        status=payload.status,
        evidence_artifacts=payload.evidence_artifacts,
    )
    db.add(defense_session)
    await db.flush()
    await persist_defense_evidence(db, defense_session)
    await db.commit()
    await db.refresh(defense_session)
    return _serialize_defense_session(defense_session)


@app.get("/api/v1/defense-sessions", response_model=list[DefenseSessionRecord])
async def list_defense_sessions(
    module_id: str | None = None,
    learner_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[DefenseSessionRecord]:
    stmt = select(DefenseSessionModel).order_by(DefenseSessionModel.created_at.desc())
    if module_id is not None:
        stmt = stmt.where(DefenseSessionModel.module_id == module_id)
    if learner_id is not None:
        stmt = stmt.where(DefenseSessionModel.learner_id == learner_id)

    result = await db.execute(stmt)
    return [_serialize_defense_session(item) for item in result.scalars().all()]


@app.get("/api/v1/defense-sessions/{session_id}", response_model=DefenseSessionRecord)
async def get_defense_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> DefenseSessionRecord:
    result = await db.execute(select(DefenseSessionModel).where(DefenseSessionModel.session_id == session_id))
    defense_session = result.scalar_one_or_none()
    if defense_session is None:
        raise HTTPException(status_code=404, detail="Defense session not found")

    return _serialize_defense_session(defense_session)


@app.post(
    "/api/v1/review-attempts",
    response_model=ReviewAttemptRecord,
    status_code=status.HTTP_201_CREATED,
)
async def create_review_attempt(
    payload: ReviewAttemptCreate,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewAttemptRecord:
    review_attempt = ReviewAttemptModel(
        learner_id=payload.learner_id,
        reviewer_id=payload.reviewer_id,
        module_id=payload.module_id,
        code_snippet=payload.code_snippet,
        feedback=payload.feedback,
        questions=payload.questions,
        score=payload.score,
        evidence_artifacts=payload.evidence_artifacts,
    )
    db.add(review_attempt)
    await db.flush()
    await persist_review_evidence(db, review_attempt)
    await db.commit()
    await db.refresh(review_attempt)
    return _serialize_review_attempt(review_attempt)


@app.get("/api/v1/review-attempts", response_model=list[ReviewAttemptRecord])
async def list_review_attempts(
    module_id: str | None = None,
    learner_id: str | None = None,
    reviewer_id: str | None = None,
    db: AsyncSession = Depends(get_db_session),
) -> list[ReviewAttemptRecord]:
    stmt = select(ReviewAttemptModel).order_by(ReviewAttemptModel.created_at.desc())
    if module_id is not None:
        stmt = stmt.where(ReviewAttemptModel.module_id == module_id)
    if learner_id is not None:
        stmt = stmt.where(ReviewAttemptModel.learner_id == learner_id)
    if reviewer_id is not None:
        stmt = stmt.where(ReviewAttemptModel.reviewer_id == reviewer_id)

    result = await db.execute(stmt)
    return [_serialize_review_attempt(item) for item in result.scalars().all()]


@app.get("/api/v1/review-attempts/{attempt_id}", response_model=ReviewAttemptRecord)
async def get_review_attempt(
    attempt_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> ReviewAttemptRecord:
    result = await db.execute(select(ReviewAttemptModel).where(ReviewAttemptModel.id == attempt_id))
    review_attempt = result.scalar_one_or_none()
    if review_attempt is None:
        raise HTTPException(status_code=404, detail="Review attempt not found")

    return _serialize_review_attempt(review_attempt)


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

    # Persist to the PostgreSQL-backed progression state under the checkpoints key
    progression_data = load_progression()
    checkpoints = progression_data.setdefault("checkpoints", [])
    checkpoints.append(record.model_dump())
    write_progression(progression_data)
    module_track_id = str(module.get("track_id", ""))
    if not module_track_id:
        module_context = _find_module(payload.module_id)
        module_track_id = str(module_context[0]["id"])
    emit_event(
        "checkpoint_submitted",
        learner_id="default",
        track_id=module_track_id,
        module_id=payload.module_id,
        checkpoint_index=payload.checkpoint_index,
        payload={
            "type": payload.type,
            "self_evaluation": payload.self_evaluation,
            "submitted_at": now,
        },
    )
    persist_checkpoint_evidence(record)

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


# ---------------------------------------------------------------------------
# Pedagogical Events
# ---------------------------------------------------------------------------


@app.post("/api/v1/events", response_model=PedagogicalEventResponse)
async def create_event(payload: PedagogicalEventCreate) -> PedagogicalEventResponse:
    event_id = await _emit_event_async(
        payload.event_type,
        learner_id=payload.learner_id,
        track_id=payload.track_id,
        module_id=payload.module_id,
        checkpoint_index=payload.checkpoint_index,
        source_service=payload.source_service,
        payload=payload.payload,
    )
    return PedagogicalEventResponse(status="recorded", event_id=event_id)
