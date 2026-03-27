from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# --- Shared type aliases ---

Track = Literal["shell", "c", "python_ai"]
Phase = Literal["foundation", "practice", "core", "advanced"]
PaceMode = Literal["slow", "normal", "intensive", "self_paced"]


# --- Endpoint response schemas (Issue #23) ---


class HealthResponse(BaseModel):
    status: str
    service: str


class MetaResponse(BaseModel):
    app: str
    campus: str
    active_course: str
    pace_mode: str


class DashboardResponse(BaseModel):
    curriculum: dict[str, Any]
    progression: dict[str, Any]


class TrackSummary(BaseModel):
    id: str
    title: str
    summary: str
    why_it_matters: str
    module_count: int


class TrackDetail(BaseModel):
    """Full track object from curriculum JSON. Extra fields preserved."""

    model_config = {"extra": "allow"}

    id: str
    title: str
    summary: str
    why_it_matters: str


class ProgressionResponse(BaseModel):
    """Top-level progression state. Extra fields preserved."""

    model_config = {"extra": "allow"}

    learning_plan: dict[str, Any] = Field(default_factory=dict)
    progress: dict[str, Any] = Field(default_factory=dict)


# --- Learner progression schemas (Issue #22) ---


class LearnerProfile(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    active_course: Track = "shell"
    active_module: str | None = None
    pace_mode: PaceMode = "normal"
    profile: dict[str, str] = Field(default_factory=dict)


class ProgressState(BaseModel):
    current_exercise: str | None = None
    current_step: str | None = None
    completed: list[str] = Field(default_factory=list)
    in_progress: list[str] = Field(default_factory=list)
    todo: list[str] = Field(default_factory=list)


class ProgressUpdate(BaseModel):
    active_course: Track | None = None
    active_module: str | None = None
    pace_mode: PaceMode | None = None
    current_exercise: str | None = None
    current_step: str | None = None
    next_command: str | None = None


# --- Module progression schemas (Issue #24) ---

ModuleStatus = Literal["not_started", "in_progress", "completed", "skipped"]


class ModuleStartRequest(BaseModel):
    """Request to start a module."""

    learner_id: str = Field(default="default", min_length=1, max_length=64)


class ModuleCompleteRequest(BaseModel):
    """Request to mark a module as completed."""

    learner_id: str = Field(default="default", min_length=1, max_length=64)


class ModuleSkipRequest(BaseModel):
    """Request to skip a module."""

    learner_id: str = Field(default="default", min_length=1, max_length=64)
    reason: str = Field(default="", max_length=500)


class ModuleStatusResponse(BaseModel):
    """Current status of a module for a learner."""

    module_id: str
    track_id: str
    status: ModuleStatus
    started_at: str | None = None
    completed_at: str | None = None
    skipped_at: str | None = None
    skip_reason: str | None = None


class ModuleProgressionResponse(BaseModel):
    """Response after a progression action (start, complete, skip)."""

    module_id: str
    track_id: str
    status: ModuleStatus
    message: str


# --- Mentor schemas ---


class MentorRequest(BaseModel):
    track_id: str = Field(default="shell")
    module_id: str | None = None
    question: str = Field(min_length=3, max_length=1000)
    pace_mode: Literal["slow", "normal", "intensive"] = "normal"
    phase: Phase = "foundation"


class MentorResponse(BaseModel):
    status: str
    observation: str
    question: str
    hint: str
    next_action: str
    source_policy: list[str]
    direct_solution_allowed: bool


