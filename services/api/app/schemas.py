from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import uuid4

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


class LearnerProfile(BaseModel):
    """Core identity of a learner on the platform."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    username: str = Field(min_length=1, max_length=64)
    active_track: Track = "shell"
    enrolled_on: date = Field(default_factory=date.today)


class Checkpoint(BaseModel):
    """A validated checkpoint within a module."""

    module_id: str
    validated_at: datetime


class ProgressState(BaseModel):
    """Tracks a learner's progression through the curriculum."""

    learner_id: str
    completed_modules: list[str] = Field(default_factory=list)
    current_module: str | None = None
    acquired_skills: list[str] = Field(default_factory=list)
    validated_checkpoints: list[Checkpoint] = Field(default_factory=list)
    phase: Phase = "foundation"
