from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
