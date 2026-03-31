"""Contextual data contracts for canonical Figma sidebars and status bars.

Issue #294 — Formalize contextual data contracts.

These Pydantic schemas mirror the frontend TypeScript contracts in
``packages/shared-types/contracts.ts``. Changes here must be reflected
there and vice versa.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


# ===================================================================
# Shared primitives
# ===================================================================

TrackId = Literal["shell", "c", "python_ai"]
Phase = Literal["foundation", "practice", "core", "advanced"]
TrustLevel = Literal["high", "medium", "low", "blocked"]
TierState = Literal["ACTIVE", "GATED", "BLOCK"]


class StatusBarContract(BaseModel):
    """HUD status bar — left + right segments."""

    left: str
    right: str


# ===================================================================
# 02 — Dashboard sidebar
# ===================================================================


class DashboardModulesContract(BaseModel):
    totalModules: int = 0
    completedModules: int = 0
    inProgressModule: str | None = None
    nextModule: str | None = None


class DashboardStreakContract(BaseModel):
    currentStreak: int = 0
    longestStreak: int = 0
    lastActiveDate: str | None = None


class DashboardDefenseContract(BaseModel):
    totalSessions: int = 0
    passedSessions: int = 0
    lastScore: float | None = None
    lastSessionDate: str | None = None


class DashboardEvidenceContract(BaseModel):
    totalItems: int = 0
    validatedItems: int = 0
    pendingItems: int = 0


class DashboardAiQueriesContract(BaseModel):
    totalQueries: int = 0
    totalRefusals: int = 0
    topTier: str | None = None


class DashboardSessionContract(BaseModel):
    activeSessions: int = 0
    attachedSession: str | None = None


class DashboardSidebarContract(BaseModel):
    """Combined sidebar contract for the Dashboard canonical page."""

    modules: DashboardModulesContract = DashboardModulesContract()
    streak: DashboardStreakContract = DashboardStreakContract()
    defense: DashboardDefenseContract = DashboardDefenseContract()
    evidence: DashboardEvidenceContract = DashboardEvidenceContract()
    aiQueries: DashboardAiQueriesContract = DashboardAiQueriesContract()
    session: DashboardSessionContract = DashboardSessionContract()


# ===================================================================
# 05 — Defense Session sidebar
# ===================================================================


class DefenseBreakdownQuestion(BaseModel):
    id: str
    label: str
    score: float | None = None
    maxScore: int = 5


class DefenseRunningScoreContract(BaseModel):
    average: float | None = None
    maxScore: int = 5


class DefenseBreakdownContract(BaseModel):
    questions: list[DefenseBreakdownQuestion] = []


class DefenseEvidenceContract(BaseModel):
    moduleId: str
    deliverable: str
    terminalSession: str | None = None
    answersCapture: int = 0


class DefenseRulesContract(BaseModel):
    timeLimitSeconds: int = 60
    noExternalDocs: bool = True
    explainReasoning: bool = True
    liveAnswerOnly: bool = True
    minimumPassScore: int = 3


class DefenseTerminalSnapshotContract(BaseModel):
    cwd: str | None = None
    lastCommand: str | None = None
    buildStatus: str | None = None
    gitDiff: str | None = None


class DefenseSidebarContract(BaseModel):
    """Combined sidebar contract for the Defense Session canonical page."""

    runningScore: DefenseRunningScoreContract = DefenseRunningScoreContract()
    breakdown: DefenseBreakdownContract = DefenseBreakdownContract()
    evidence: DefenseEvidenceContract = DefenseEvidenceContract(
        moduleId="", deliverable=""
    )
    rules: DefenseRulesContract = DefenseRulesContract()
    terminalSnapshot: DefenseTerminalSnapshotContract = (
        DefenseTerminalSnapshotContract()
    )


# ===================================================================
# 06 — AI Mentor sidebar
# ===================================================================


class MentorSourcePolicyTier(BaseModel):
    id: str
    label: str
    state: str  # TierState


class MentorSourcePolicyContract(BaseModel):
    tiers: list[MentorSourcePolicyTier] = []


class MentorModuleContextContract(BaseModel):
    track: str
    module: str
    phase: str
    skillCount: int = 0
    evidenceCount: int = 0
    mode: str = "live"


class MentorProvenanceEntry(BaseModel):
    time: str
    label: str
    state: str  # TierState | "OK" | "skip"


class MentorProvenanceContract(BaseModel):
    entries: list[MentorProvenanceEntry] = []


class MentorTerminalStateContract(BaseModel):
    sessionName: str | None = None
    context: str = "OFF"  # "INJECTED" | "OFF"
    gateway: str = "LIVE"  # "LIVE" | "DEMO"


class MentorObservationEntry(BaseModel):
    time: str
    text: str


class MentorObservationsContract(BaseModel):
    entries: list[MentorObservationEntry] = []


class MentorSessionStatsContract(BaseModel):
    queries: int = 0
    responses: int = 0
    refusals: int = 0
    latency: str = "n/a"
    intent: str = "awaiting"


class MentorSidebarContract(BaseModel):
    """Combined sidebar contract for the AI Mentor canonical page."""

    sourcePolicy: MentorSourcePolicyContract = MentorSourcePolicyContract()
    moduleContext: MentorModuleContextContract = MentorModuleContextContract(
        track="shell", module="", phase="foundation"
    )
    provenance: MentorProvenanceContract = MentorProvenanceContract()
    terminalState: MentorTerminalStateContract = MentorTerminalStateContract()
    observations: MentorObservationsContract = MentorObservationsContract()
    sessionStats: MentorSessionStatsContract = MentorSessionStatsContract()


# ===================================================================
# App Shell runtime
# ===================================================================


class AppShellSessionContract(BaseModel):
    userId: str | None = None
    login: str | None = None
    email: str | None = None
    track: str | None = None
    isAuthenticated: bool = False
    expiresAt: str | None = None


class AppShellRuntimeContract(BaseModel):
    version: str = "1.0"
    sourceMode: str = "live"
    terminalAvailable: bool = False
    activeTerminalSession: str | None = None


class AppShellContract(BaseModel):
    """Combined contract for shell-level runtime data."""

    session: AppShellSessionContract = AppShellSessionContract()
    runtime: AppShellRuntimeContract = AppShellRuntimeContract()
