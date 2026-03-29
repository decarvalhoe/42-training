from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

# --- Shared type aliases ---

Track = Literal["shell", "c", "python_ai"]
Phase = Literal["foundation", "practice", "core", "advanced"]
PaceMode = Literal["slow", "normal", "intensive", "self_paced"]
ModuleStatus = Literal["not_started", "in_progress", "completed", "skipped"]


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
    """Persisted learner identity and current track context."""

    id: str = Field(min_length=1, max_length=64)
    login: str = Field(min_length=1, max_length=64)
    track: Track
    current_module: str | None = None
    started_at: datetime
    updated_at: datetime


class ProfileCreateRequest(BaseModel):
    track: Track
    login: str | None = Field(default=None, min_length=1, max_length=64)
    current_module: str | None = Field(default=None, max_length=128)
    activate: bool = True


class ProfileResponse(BaseModel):
    id: str
    login: str
    track: Track
    current_module: str | None = None
    started_at: datetime
    updated_at: datetime


class ProfilesResponse(BaseModel):
    active_profile_id: str | None = None
    active_profile: ProfileResponse | None = None
    profiles: list[ProfileResponse] = Field(default_factory=list)


class ProgressState(BaseModel):
    """Progress record for a learner on a specific module."""

    module_id: str = Field(min_length=1)
    status: ModuleStatus
    started_at: datetime
    completed_at: datetime | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class ProgressUpdate(BaseModel):
    active_course: Track | None = None
    active_module: str | None = None
    pace_mode: PaceMode | None = None
    current_exercise: str | None = None
    current_step: str | None = None
    next_command: str | None = None


# --- Module progression schemas (Issue #24) ---


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


# --- Checkpoint, Review, DefenseSession schemas (Issue #36) ---

CheckpointType = Literal["exit_criteria", "deliverable", "skill_check"]
DefenseStatus = Literal["scheduled", "in_progress", "passed", "failed"]


class Checkpoint(BaseModel):
    """A verifiable checkpoint within a module.

    Checkpoints represent self-assessment gates. The learner submits
    evidence (command output, explanation, file) and the system evaluates
    it against success_criteria.
    """

    module_id: str = Field(min_length=1)
    type: CheckpointType
    prompt: str = Field(min_length=3, max_length=2000)
    success_criteria: list[str] = Field(min_length=1)
    evidence: str = Field(default="", max_length=5000)


class Review(BaseModel):
    """A peer-review submission aligned with 42 pair-review culture.

    Reviews capture structured feedback on a learner's work: the code or
    command output being reviewed, qualitative feedback, and questions
    the reviewer would ask in a real evaluation.
    """

    reviewer_id: str = Field(min_length=1, max_length=64)
    module_id: str = Field(min_length=1)
    code_snippet: str = Field(min_length=1, max_length=10000)
    feedback: str = Field(min_length=3, max_length=5000)
    questions: list[str] = Field(default_factory=list)
    score: int | None = Field(default=None, ge=0, le=100)


class DefenseSession(BaseModel):
    """An oral defense session modeled after 42 project evaluations.

    Defense sessions track the Q&A exchange between an examiner agent
    and a learner, producing per-question scores and an overall status.
    """

    session_id: str = Field(min_length=1, max_length=64)
    module_id: str = Field(min_length=1)
    questions: list[str] = Field(min_length=1)
    answers: list[str] = Field(default_factory=list)
    scores: list[int] = Field(default_factory=list)
    status: DefenseStatus = "scheduled"


class DefenseSessionCreate(DefenseSession):
    learner_id: str | None = Field(default=None, min_length=1, max_length=64)
    evidence_artifacts: list[dict[str, Any]] = Field(default_factory=list)


class DefenseSessionRecord(DefenseSessionCreate):
    created_at: datetime
    updated_at: datetime


class ReviewAttemptCreate(Review):
    learner_id: str | None = Field(default=None, min_length=1, max_length=64)
    evidence_artifacts: list[dict[str, Any]] = Field(default_factory=list)


class ReviewAttemptRecord(ReviewAttemptCreate):
    id: str = Field(min_length=1, max_length=64)
    created_at: datetime
    updated_at: datetime


# --- Checkpoint submission schemas (Issue #37) ---

EvaluationResult = Literal["pass", "partial", "fail"]


class CheckpointSubmission(BaseModel):
    """Payload for submitting evidence against a checkpoint."""

    module_id: str = Field(min_length=1)
    checkpoint_index: int = Field(ge=0)
    type: CheckpointType = "exit_criteria"
    evidence: str = Field(min_length=1, max_length=10000)
    self_evaluation: EvaluationResult


class CheckpointRecord(BaseModel):
    """Stored record of a checkpoint submission and its evaluation."""

    module_id: str
    checkpoint_index: int
    type: CheckpointType
    prompt: str
    evidence: str
    self_evaluation: EvaluationResult
    submitted_at: str


class CheckpointListResponse(BaseModel):
    """Response listing checkpoints for a module with submission status."""

    module_id: str
    checkpoints: list[dict[str, object]]


PedagogicalEventType = Literal[
    "module_started",
    "module_completed",
    "checkpoint_submitted",
    "mentor_query",
    "defense_started",
]


class PedagogicalEventCreate(BaseModel):
    event_type: PedagogicalEventType
    learner_id: str | None = "default"
    track_id: str | None = None
    module_id: str | None = None
    checkpoint_index: int | None = Field(default=None, ge=0)
    source_service: Literal["api", "ai_gateway"] = "api"
    payload: dict[str, Any] = Field(default_factory=dict)


class PedagogicalEventResponse(BaseModel):
    status: str
    event_id: str | None = None


class AnalyticsSummary(BaseModel):
    total_events: int
    module_completions: int
    average_completion_minutes: float
    checkpoint_success_rate: float
    mentor_queries: int
    defenses_started: int


class AnalyticsChartRow(BaseModel):
    module_id: str
    module_title: str
    track_id: str
    phase: str
    value: float
    count: int
    suffix: str


class AnalyticsDashboardResponse(BaseModel):
    summary: AnalyticsSummary
    modules_completed: list[AnalyticsChartRow]
    average_time: list[AnalyticsChartRow]
    success_rate: list[AnalyticsChartRow]
