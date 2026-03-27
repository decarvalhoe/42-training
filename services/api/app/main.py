from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .repository import CurriculumRepository, repo
from .schemas import ProgressUpdate

app = FastAPI(title="42-training API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_repo() -> CurriculumRepository:
    """Return the active repository.  Override in tests via app.dependency_overrides."""
    return repo


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/api/v1/meta")
def meta(r: CurriculumRepository = Depends(get_repo)) -> dict[str, object]:
    curriculum = r.get_curriculum()
    progression = r.get_progression()
    return {
        "app": "42-training",
        "campus": curriculum["metadata"]["campus"],
        "active_course": progression.get("learning_plan", {}).get(
            "active_course", "shell"
        ),
        "pace_mode": progression.get("learning_plan", {}).get(
            "pace_mode", "self_paced"
        ),
    }


@app.get("/api/v1/dashboard")
def dashboard(r: CurriculumRepository = Depends(get_repo)) -> dict[str, object]:
    return {
        "curriculum": r.get_curriculum(),
        "progression": r.get_progression(),
    }


@app.get("/api/v1/tracks")
def tracks(r: CurriculumRepository = Depends(get_repo)) -> list[dict[str, object]]:
    return r.get_tracks()


@app.get("/api/v1/tracks/{track_id}")
def track_detail(
    track_id: str, r: CurriculumRepository = Depends(get_repo)
) -> dict[str, object]:
    track = r.get_track(track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@app.get("/api/v1/progression")
def progression(r: CurriculumRepository = Depends(get_repo)) -> dict[str, object]:
    return r.get_progression()


@app.post("/api/v1/progression")
def update_progression(
    payload: ProgressUpdate, r: CurriculumRepository = Depends(get_repo)
) -> dict[str, object]:
    updates = payload.model_dump(exclude_none=True)
    return r.update_progression(updates)
