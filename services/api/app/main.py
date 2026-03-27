from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .repository import load_curriculum, load_progression, write_progression

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
    curriculum = load_curriculum()
    progression = load_progression()
    return {
        "app": "42-training",
        "campus": curriculum["metadata"]["campus"],
        "active_course": progression.get("learning_plan", {}).get("active_course", "shell"),
        "pace_mode": progression.get("learning_plan", {}).get("pace_mode", "self_paced"),
    }


@app.get("/api/v1/dashboard")
def dashboard() -> dict[str, object]:
    return {
        "curriculum": load_curriculum(),
        "progression": load_progression(),
    }


@app.get("/api/v1/tracks")
def tracks() -> list[dict[str, object]]:
    curriculum = load_curriculum()
    result: list[dict[str, object]] = []
    for track in curriculum["tracks"]:
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
    curriculum = load_curriculum()
    for track in curriculum["tracks"]:
        if track["id"] == track_id:
            return track
    raise HTTPException(status_code=404, detail="Track not found")


@app.get("/api/v1/progression")
def progression() -> dict[str, object]:
    return load_progression()


@app.post("/api/v1/progression")
def update_progression(payload: dict[str, object]) -> dict[str, object]:
    current = load_progression()
    learning_plan = current.setdefault("learning_plan", {})
    progress = current.setdefault("progress", {})

    for key in ("active_course", "active_module", "pace_mode"):
        if key in payload:
            learning_plan[key] = payload[key]

    for key in ("current_exercise", "current_step"):
        if key in payload:
            progress[key] = payload[key]

    if "next_command" in payload:
        current["next_command"] = payload["next_command"]

    write_progression(current)
    return current
