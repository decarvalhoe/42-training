from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TrackSummary(BaseModel):
    id: str
    title: str
    summary: str
    why_it_matters: str
    module_count: int


class MentorRequest(BaseModel):
    track_id: str = Field(default="shell")
    module_id: str | None = None
    question: str = Field(min_length=3, max_length=1000)
    pace_mode: Literal["slow", "normal", "intensive"] = "normal"
    phase: Literal["foundation", "practice", "core", "advanced"] = "foundation"


class MentorResponse(BaseModel):
    status: str
    observation: str
    question: str
    hint: str
    next_action: str
    source_policy: list[str]
    direct_solution_allowed: bool


# --- Learner profile & progression schemas (Issue #22) ---

Track = Literal["shell", "c", "python_ai"]
Phase = Literal["foundation", "practice", "core", "advanced"]
PaceMode = Literal["slow", "normal", "intensive", "self_paced"]


class LearnerProfile(BaseModel):
    """Core identity of a learner on the platform."""

    username: str = Field(min_length=1, max_length=64)
    active_course: Track = "shell"
    active_module: str | None = None
    pace_mode: PaceMode = "normal"
    profile: dict[str, str] = Field(default_factory=dict)


class ProgressState(BaseModel):
    """Tracks a learner's current progression state."""

    current_exercise: str | None = None
    current_step: str | None = None
    completed: list[str] = Field(default_factory=list)
    in_progress: list[str] = Field(default_factory=list)
    todo: list[str] = Field(default_factory=list)


class ProgressUpdate(BaseModel):
    """Payload for POST /api/v1/progression."""

    active_course: Track | None = None
    active_module: str | None = None
    pace_mode: PaceMode | None = None
    current_exercise: str | None = None
    current_step: str | None = None
    next_command: str | None = None
