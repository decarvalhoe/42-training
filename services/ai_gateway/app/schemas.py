from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MentorRequest(BaseModel):
    learner_id: str = Field(default="default", min_length=1, max_length=64)
    track_id: str = Field(default="shell")
    module_id: str | None = None
    question: str = Field(min_length=3, max_length=1000)
    pace_mode: Literal["slow", "normal", "intensive"] = "normal"
    phase: Literal["foundation", "practice", "core", "advanced"] = "foundation"


IntentRole = Literal["mentor", "librarian", "reviewer", "examiner"]


class IntentRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)
    track_id: str | None = None
    module_id: str | None = None
    phase: Literal["foundation", "practice", "core", "advanced"] = "foundation"


class IntentResponse(BaseModel):
    status: str
    active_role: IntentRole
    route: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    classifier: Literal["llm", "fallback"]


class SourceUsed(BaseModel):
    tier: str
    label: str
    url: str | None = None


class MentorResponse(BaseModel):
    status: str
    observation: str
    question: str
    hint: str
    next_action: str
    source_policy: list[str]
    direct_solution_allowed: bool
    sources_used: list[SourceUsed]
    confidence_level: Literal["high", "medium", "low"]
    reasoning_trace: str


class LibrarianRequest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    track_id: str | None = None
    module_id: str | None = None
    phase: Literal["foundation", "practice", "core", "advanced"] = "foundation"
    max_results: int = Field(default=5, ge=1, le=20)


class AuthorizedSourceResource(BaseModel):
    label: str
    url: str | None = None


class AuthorizedSource(BaseModel):
    tier: str
    tier_label: str
    allowed_usage: str
    confidence_level: str
    confidence_rationale: str
    resources: list[AuthorizedSourceResource]


class LibrarianProvenance(BaseModel):
    tier: str
    tier_label: str
    source_label: str
    source_url: str | None = None
    allowed_usage: str
    confidence_level: str
    confidence_rationale: str


class LibrarianResult(BaseModel):
    content: str
    source_url: str | None = None
    tier: str
    tier_label: str
    confidence: float
    provenance: LibrarianProvenance


class LibrarianResponse(BaseModel):
    status: str
    query: str
    results: list[LibrarianResult]
    tiers_used: list[str]
    blocked_tiers: list[str]
    authorized_sources: list[AuthorizedSource]
    sources_used: list[LibrarianProvenance]


class ReviewerRequest(BaseModel):
    code: str = Field(min_length=1, max_length=5000)
    track_id: str = Field(default="shell")
    module_id: str | None = None
    phase: Literal["foundation", "practice", "core", "advanced"] = "foundation"
    language: Literal["shell", "c", "python"] = "shell"


class ReviewerResponse(BaseModel):
    status: str
    observation: str
    questions: list[str]
    hint: str
    next_action: str
    corrected_code: None = Field(
        default=None,
        description="Always null — the Reviewer never provides corrected code",
    )
    guardrail_clean: bool = Field(
        default=True,
        description="False when guardrails scrubbed solution leakage from the output",
    )
    guardrail_scrubbed_fields: list[str] = Field(
        default_factory=list,
        description="Fields that were scrubbed by guardrails",
    )


# --- Defense (oral defense MVP) ---


class DefenseStartRequest(BaseModel):
    track_id: str
    module_id: str
    learner_id: str | None = Field(default=None, min_length=1, max_length=64)
    reviewer_id: str | None = Field(default=None, min_length=1, max_length=64)
    phase: Literal["foundation", "practice", "core", "advanced"] = "foundation"
    num_questions: int = Field(default=3, ge=1, le=10)
    question_time_limit_seconds: int = Field(default=60, ge=10, le=600)


class DefenseQuestionOut(BaseModel):
    question_id: str
    text: str
    skill: str
    time_limit_seconds: int


class DefenseStartResponse(BaseModel):
    status: str
    session_id: str
    track_id: str
    module_id: str
    questions: list[DefenseQuestionOut]
    total_questions: int
    question_time_limit_seconds: int
    active_question_id: str | None
    started_at: datetime
    current_question_deadline: datetime | None


class DefenseAnswerRequest(BaseModel):
    session_id: str
    question_id: str
    answer: str = Field(min_length=1, max_length=5000)


class DefenseAnswerResponse(BaseModel):
    status: str
    question_id: str
    score: float
    feedback: str
    questions_remaining: int
    timed_out: bool
    elapsed_seconds: float
    next_question_id: str | None = None
    next_question_deadline: datetime | None = None


class DefenseQuestionResult(BaseModel):
    question_id: str
    question: str
    skill: str
    score: float
    feedback: str
    answered: bool
    timed_out: bool = False
    elapsed_seconds: float = 0.0


class DefenseResultResponse(BaseModel):
    status: str
    session_id: str
    overall_score: float
    passed: bool
    summary: str
    timed_out_questions: int
    question_results: list[DefenseQuestionResult]
