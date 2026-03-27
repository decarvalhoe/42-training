from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .repository import load_curriculum, load_progression, write_progression
from .schemas import (
    DashboardResponse,
    HealthResponse,
    MetaResponse,
    ProgressionResponse,
    ProgressUpdate,
    TrackDetail,
    TrackSummary,
)

app = FastAPI(title="42-training API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api")


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


@app.get("/api/v1/dashboard")
def dashboard() -> DashboardResponse:
    return DashboardResponse(
        curriculum=load_curriculum(),
        progression=load_progression(),
    )


@app.get("/api/v1/tracks")
def tracks() -> list[TrackSummary]:
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


@app.get("/api/v1/tracks/{track_id}")
def track_detail(track_id: str) -> TrackDetail:
    curriculum = load_curriculum()
    for track in curriculum["tracks"]:
        if track["id"] == track_id:
            return TrackDetail(**track)
    raise HTTPException(status_code=404, detail="Track not found")


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

    write_progression(current)
    return ProgressionResponse(**current)
