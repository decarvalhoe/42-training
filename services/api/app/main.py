from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .repository import get_repository
from .schemas import ProgressUpdate

app = FastAPI(title="42-training API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/api/v1/meta")
def meta() -> dict[str, object]:
    repo = get_repository()
    curriculum = repo.get_curriculum()
    progression = repo.get_progression()
    return {
        "app": "42-training",
        "campus": curriculum["metadata"]["campus"],
        "active_course": progression.get("learning_plan", {}).get("active_course", "shell"),
        "pace_mode": progression.get("learning_plan", {}).get("pace_mode", "self_paced"),
    }


@app.get("/api/v1/dashboard")
def dashboard() -> dict[str, object]:
    repo = get_repository()
    return {
        "curriculum": repo.get_curriculum(),
        "progression": repo.get_progression(),
    }


@app.get("/api/v1/tracks")
def tracks() -> list[dict[str, object]]:
    repo = get_repository()
    result: list[dict[str, object]] = []
    for track in repo.get_tracks():
        result.append(
            {
                "id": track["id"],
                "title": track["title"],
                "summary": track["summary"],
                "why_it_matters": track["why_it_matters"],
                "module_count": len(track.get("modules", [])),
            }
        )
    return result


@app.get("/api/v1/tracks/{track_id}")
def track_detail(track_id: str) -> dict[str, object]:
    repo = get_repository()
    track = repo.get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@app.get("/api/v1/progression")
def progression() -> dict[str, object]:
    return get_repository().get_progression()


@app.post("/api/v1/progression")
def update_progression(payload: ProgressUpdate) -> dict[str, object]:
    repo = get_repository()
    current = repo.get_progression()
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

    repo.update_progression(current)
    return current
