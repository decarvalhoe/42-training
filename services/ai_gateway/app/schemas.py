from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MentorRequest(BaseModel):
    track_id: str = Field(default="shell")
    module_id: str | None = None
    question: str = Field(min_length=3, max_length=1000)
    pace_mode: Literal["slow", "normal", "intensive"] = "normal"
    phase: Literal["foundation", "practice", "core", "advanced"] = "foundation"


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


class LibrarianResult(BaseModel):
    content: str
    source_url: str | None = None
    tier: str
    tier_label: str
    confidence: float


class LibrarianResponse(BaseModel):
    status: str
    query: str
    results: list[LibrarianResult]
    tiers_used: list[str]
    blocked_tiers: list[str]


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


# --- Defense (oral defense MVP) ---


class DefenseStartRequest(BaseModel):
    track_id: str
    module_id: str
    phase: Literal["foundation", "practice", "core", "advanced"] = "foundation"
    num_questions: int = Field(default=3, ge=1, le=10)


class DefenseQuestionOut(BaseModel):
    question_id: str
    text: str
    skill: str


class DefenseStartResponse(BaseModel):
    status: str
    session_id: str
    track_id: str
    module_id: str
    questions: list[DefenseQuestionOut]
    total_questions: int


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


class DefenseQuestionResult(BaseModel):
    question_id: str
    question: str
    skill: str
    score: float
    feedback: str
    answered: bool


class DefenseResultResponse(BaseModel):
    status: str
    session_id: str
    overall_score: float
    passed: bool
    summary: str
    question_results: list[DefenseQuestionResult]
