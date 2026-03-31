/**
 * Contextual data contracts for canonical Figma sidebars and status bars.
 *
 * Issue #294 — Formalize contextual data contracts.
 *
 * Each canonical page (Dashboard, Track Explorer, Module Learning,
 * Defense Session, AI Mentor) has a typed contract for the data that
 * feeds its sidebar sections and status bar.
 *
 * Off-canonical features (review, evidence, profiles, sessions,
 * analytics) are data providers only — they feed these contracts
 * but do not impose additional UI surfaces.
 *
 * Backend Pydantic schemas should mirror these contracts.
 */

// ===================================================================
// Shared primitives
// ===================================================================

/** Track identifier. */
export type TrackId = "shell" | "c" | "python_ai";

/** Module lifecycle phase. */
export type Phase = "foundation" | "practice" | "core" | "advanced";

/** Source governance trust level. */
export type TrustLevel = "high" | "medium" | "low" | "blocked";

/** Source policy tier identifier. */
export type SourcePolicyTierId =
  | "official_42"
  | "community_docs"
  | "testers_and_tooling"
  | "solution_metadata"
  | "blocked_solution_content";

/** Source policy tier state as displayed in sidebar. */
export type TierState = "ACTIVE" | "GATED" | "BLOCK";

/** HUD status bar — left + right segments. */
export type StatusBarContract = {
  left: string;
  right: string;
};

// ===================================================================
// 02 — Dashboard sidebar contracts
// ===================================================================

export type DashboardModulesContract = {
  totalModules: number;
  completedModules: number;
  inProgressModule: string | null;
  nextModule: string | null;
};

export type DashboardStreakContract = {
  currentStreak: number;
  longestStreak: number;
  lastActiveDate: string | null;
};

export type DashboardDefenseContract = {
  totalSessions: number;
  passedSessions: number;
  lastScore: number | null;
  lastSessionDate: string | null;
};

export type DashboardEvidenceContract = {
  totalItems: number;
  validatedItems: number;
  pendingItems: number;
};

export type DashboardAiQueriesContract = {
  totalQueries: number;
  totalRefusals: number;
  topTier: string | null;
};

export type DashboardSessionContract = {
  activeSessions: number;
  attachedSession: string | null;
};

/** Combined sidebar contract for the Dashboard canonical page. */
export type DashboardSidebarContract = {
  modules: DashboardModulesContract;
  streak: DashboardStreakContract;
  defense: DashboardDefenseContract;
  evidence: DashboardEvidenceContract;
  aiQueries: DashboardAiQueriesContract;
  session: DashboardSessionContract;
};

// ===================================================================
// 03 — Track Explorer sidebar contracts
// ===================================================================

export type TrackModuleContract = {
  moduleId: string;
  moduleName: string;
};

export type TrackStatusContract = {
  status: "not_started" | "in_progress" | "completed" | "skipped";
};

export type TrackSkillsContract = {
  skills: Array<{ name: string; completed: boolean }>;
};

export type TrackPrerequisitesContract = {
  prerequisites: Array<{ moduleId: string; name: string; status: "DONE" | "pending" }>;
};

export type TrackEvidenceContract = {
  capturedCount: number;
  validCount: number;
  items: Array<{ name: string; type: "code" | "screenshot" | "log" }>;
};

export type TrackTerminalContract = {
  sessionName: string | null;
  status: "LIVE" | "standby" | "detached";
  latency: string | null;
  cwd: string | null;
  buildStatus: string | null;
  testsSummary: string | null;
};

/** Combined sidebar contract for the Track Explorer canonical page. */
export type TrackExplorerSidebarContract = {
  module: TrackModuleContract;
  status: TrackStatusContract;
  skills: TrackSkillsContract;
  prerequisites: TrackPrerequisitesContract;
  evidence: TrackEvidenceContract;
  terminal: TrackTerminalContract;
};

// ===================================================================
// 04 — Module Learning sidebar contracts
// ===================================================================

export type ModuleObjectivesContract = {
  objectives: Array<{ key: string; label: string; completed: boolean }>;
};

export type ModuleAiHintContract = {
  hint: string | null;
  source: string | null;
  confidence: TrustLevel | null;
};

export type ModuleSourceContract = {
  tier: string;
  confidence: TrustLevel;
};

export type ModuleReferencesContract = {
  references: Array<{ label: string; tier: "official" | "community"; url?: string }>;
};

export type ModuleTerminalContract = {
  sessionName: string | null;
  status: "LIVE" | "standby" | "detached";
  latency: string | null;
  cwd: string | null;
  lastCommand: string | null;
  buildStatus: string | null;
};

export type ModuleActionsContract = {
  canSubmitEvidence: boolean;
  canAskMentor: boolean;
};

/** Combined sidebar contract for the Module Learning canonical page. */
export type ModuleLearSidebarContract = {
  objectives: ModuleObjectivesContract;
  aiHint: ModuleAiHintContract;
  source: ModuleSourceContract;
  references: ModuleReferencesContract;
  terminal: ModuleTerminalContract;
  actions: ModuleActionsContract;
};

// ===================================================================
// 05 — Defense Session sidebar contracts
// ===================================================================

export type DefenseRunningScoreContract = {
  average: number | null;
  maxScore: number;
};

export type DefenseBreakdownContract = {
  questions: Array<{
    id: string;
    label: string;
    score: number | null;
    maxScore: number;
  }>;
};

export type DefenseEvidenceContract = {
  moduleId: string;
  deliverable: string;
  terminalSession: string | null;
  answersCapture: number;
};

export type DefenseRulesContract = {
  timeLimitSeconds: number;
  noExternalDocs: boolean;
  explainReasoning: boolean;
  liveAnswerOnly: boolean;
  minimumPassScore: number;
};

export type DefenseTerminalSnapshotContract = {
  cwd: string | null;
  lastCommand: string | null;
  buildStatus: string | null;
  gitDiff: string | null;
};

/** Combined sidebar contract for the Defense Session canonical page. */
export type DefenseSidebarContract = {
  runningScore: DefenseRunningScoreContract;
  breakdown: DefenseBreakdownContract;
  evidence: DefenseEvidenceContract;
  rules: DefenseRulesContract;
  terminalSnapshot: DefenseTerminalSnapshotContract;
};

// ===================================================================
// 06 — AI Mentor sidebar contracts
// ===================================================================

export type MentorSourcePolicyContract = {
  tiers: Array<{
    id: SourcePolicyTierId | string;
    label: string;
    state: TierState;
  }>;
};

export type MentorModuleContextContract = {
  track: TrackId | string;
  module: string;
  phase: Phase | string;
  skillCount: number;
  evidenceCount: number;
  mode: "live" | "demo";
};

export type MentorProvenanceContract = {
  entries: Array<{
    time: string;
    label: string;
    state: TierState | "OK" | "skip";
  }>;
};

export type MentorTerminalStateContract = {
  sessionName: string | null;
  context: "INJECTED" | "OFF";
  gateway: "LIVE" | "DEMO";
};

export type MentorObservationsContract = {
  entries: Array<{
    time: string;
    text: string;
  }>;
};

export type MentorSessionStatsContract = {
  queries: number;
  responses: number;
  refusals: number;
  latency: string;
  intent: string;
};

/** Combined sidebar contract for the AI Mentor canonical page. */
export type MentorSidebarContract = {
  sourcePolicy: MentorSourcePolicyContract;
  moduleContext: MentorModuleContextContract;
  provenance: MentorProvenanceContract;
  terminalState: MentorTerminalStateContract;
  observations: MentorObservationsContract;
  sessionStats: MentorSessionStatsContract;
};

// ===================================================================
// Login / App Shell runtime contracts
// ===================================================================

export type AppShellSessionContract = {
  userId: string | null;
  login: string | null;
  email: string | null;
  track: TrackId | null;
  isAuthenticated: boolean;
  expiresAt: string | null;
};

export type AppShellRuntimeContract = {
  version: string;
  sourceMode: "live" | "demo";
  terminalAvailable: boolean;
  activeTerminalSession: string | null;
};

/** Combined contract for shell-level runtime data. */
export type AppShellContract = {
  session: AppShellSessionContract;
  runtime: AppShellRuntimeContract;
};
