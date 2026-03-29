export type EvidenceArtifact = {
  kind: string;
  label: string;
  content: string;
};

export type ReviewAttemptRecord = {
  id: string;
  learnerId: string | null;
  reviewerId: string;
  moduleId: string;
  codeSnippet: string;
  feedback: string;
  questions: string[];
  score: number | null;
  evidenceArtifacts: EvidenceArtifact[];
  createdAt: string;
  updatedAt: string;
};

export type DefenseSessionRecord = {
  sessionId: string;
  learnerId: string | null;
  moduleId: string;
  questions: string[];
  answers: string[];
  scores: number[];
  status: string;
  evidenceArtifacts: EvidenceArtifact[];
  createdAt: string;
  updatedAt: string;
};

export type ReviewAttemptCreatePayload = {
  learnerId?: string;
  reviewerId: string;
  moduleId: string;
  codeSnippet: string;
  feedback: string;
  questions: string[];
  score?: number;
  evidenceArtifacts: EvidenceArtifact[];
};

export type AssessmentFeed = {
  reviewAttempts: ReviewAttemptRecord[];
  defenseSessions: DefenseSessionRecord[];
  mocked: boolean;
};

type ApiReviewAttemptRecord = {
  id: string;
  learner_id?: string | null;
  reviewer_id: string;
  module_id: string;
  code_snippet: string;
  feedback: string;
  questions?: string[];
  score?: number | null;
  evidence_artifacts?: Array<Record<string, unknown>>;
  created_at?: string;
  updated_at?: string;
};

type ApiDefenseSessionRecord = {
  session_id: string;
  learner_id?: string | null;
  module_id: string;
  questions?: string[];
  answers?: string[];
  scores?: number[];
  status: string;
  evidence_artifacts?: Array<Record<string, unknown>>;
  created_at?: string;
  updated_at?: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REVIEW_STORAGE_KEY = "training-mock-review-attempts";
const DEFENSE_STORAGE_KEY = "training-mock-defense-sessions";

function nowIso() {
  return new Date().toISOString();
}

function randomId(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function normalizeArtifact(input: Record<string, unknown>): EvidenceArtifact {
  return {
    kind: typeof input.kind === "string" ? input.kind : "note",
    label: typeof input.label === "string" ? input.label : "Artifact",
    content: typeof input.content === "string" ? input.content : "",
  };
}

function mapReviewAttempt(record: ApiReviewAttemptRecord): ReviewAttemptRecord {
  return {
    id: record.id,
    learnerId: record.learner_id ?? null,
    reviewerId: record.reviewer_id,
    moduleId: record.module_id,
    codeSnippet: record.code_snippet,
    feedback: record.feedback,
    questions: record.questions ?? [],
    score: record.score ?? null,
    evidenceArtifacts: (record.evidence_artifacts ?? []).map(normalizeArtifact),
    createdAt: record.created_at ?? nowIso(),
    updatedAt: record.updated_at ?? nowIso(),
  };
}

function mapDefenseSession(record: ApiDefenseSessionRecord): DefenseSessionRecord {
  return {
    sessionId: record.session_id,
    learnerId: record.learner_id ?? null,
    moduleId: record.module_id,
    questions: record.questions ?? [],
    answers: record.answers ?? [],
    scores: record.scores ?? [],
    status: record.status,
    evidenceArtifacts: (record.evidence_artifacts ?? []).map(normalizeArtifact),
    createdAt: record.created_at ?? nowIso(),
    updatedAt: record.updated_at ?? nowIso(),
  };
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Assessment API returned ${response.status}`);
  }

  return response.json() as Promise<T>;
}

function seedReviewAttempts(): ReviewAttemptRecord[] {
  const timestamp = nowIso();
  return [
    {
      id: randomId("review"),
      learnerId: "default",
      reviewerId: "peer-shell",
      moduleId: "shell-basics",
      codeSnippet: "ls -la\nmkdir sandbox\ncd sandbox\n",
      feedback: "Clear command sequence. Review file permissions and explain why each command is needed.",
      questions: [
        "How would you verify hidden files are present?",
        "Which command would you use to inspect permissions before chmod?",
      ],
      score: 78,
      evidenceArtifacts: [
        { kind: "command-output", label: "Terminal output", content: "drwxr-xr-x sandbox\n-rw-r--r-- hello.txt" },
        { kind: "self-note", label: "Learner note", content: "Confident on navigation, less sure on permissions." },
      ],
      createdAt: timestamp,
      updatedAt: timestamp,
    },
  ];
}

function seedDefenseSessions(): DefenseSessionRecord[] {
  const timestamp = nowIso();
  return [
    {
      sessionId: randomId("defense"),
      learnerId: "default",
      moduleId: "c-memory",
      questions: ["Explain the difference between stack allocation and heap allocation."],
      answers: ["Stack is automatic and scoped, heap is manual and survives until free."],
      scores: [82],
      status: "passed",
      evidenceArtifacts: [
        { kind: "oral-summary", label: "Defense summary", content: "Solid explanation of malloc/free lifecycle." },
      ],
      createdAt: timestamp,
      updatedAt: timestamp,
    },
  ];
}

function readStoredJson<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") {
    return fallback;
  }

  const stored = window.localStorage.getItem(key);
  if (!stored) {
    window.localStorage.setItem(key, JSON.stringify(fallback));
    return fallback;
  }

  try {
    return JSON.parse(stored) as T;
  } catch {
    window.localStorage.setItem(key, JSON.stringify(fallback));
    return fallback;
  }
}

function writeStoredJson<T>(key: string, value: T) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(key, JSON.stringify(value));
}

function readMockReviewAttempts() {
  return readStoredJson<ReviewAttemptRecord[]>(REVIEW_STORAGE_KEY, seedReviewAttempts());
}

function readMockDefenseSessions() {
  return readStoredJson<DefenseSessionRecord[]>(DEFENSE_STORAGE_KEY, seedDefenseSessions());
}

export async function listReviewAttempts(): Promise<{ items: ReviewAttemptRecord[]; mocked: boolean }> {
  try {
    const data = await requestJson<ApiReviewAttemptRecord[]>("/api/v1/review-attempts");
    return { items: data.map(mapReviewAttempt), mocked: false };
  } catch {
    return { items: readMockReviewAttempts(), mocked: true };
  }
}

export async function createReviewAttempt(payload: ReviewAttemptCreatePayload): Promise<{ item: ReviewAttemptRecord; mocked: boolean }> {
  try {
    const data = await requestJson<ApiReviewAttemptRecord>("/api/v1/review-attempts", {
      method: "POST",
      body: JSON.stringify({
        learner_id: payload.learnerId || null,
        reviewer_id: payload.reviewerId,
        module_id: payload.moduleId,
        code_snippet: payload.codeSnippet,
        feedback: payload.feedback,
        questions: payload.questions,
        score: payload.score ?? null,
        evidence_artifacts: payload.evidenceArtifacts,
      }),
    });
    return { item: mapReviewAttempt(data), mocked: false };
  } catch {
    const timestamp = nowIso();
    const item: ReviewAttemptRecord = {
      id: randomId("review"),
      learnerId: payload.learnerId ?? null,
      reviewerId: payload.reviewerId,
      moduleId: payload.moduleId,
      codeSnippet: payload.codeSnippet,
      feedback: payload.feedback,
      questions: payload.questions,
      score: payload.score ?? null,
      evidenceArtifacts: payload.evidenceArtifacts,
      createdAt: timestamp,
      updatedAt: timestamp,
    };
    const next = [item, ...readMockReviewAttempts()];
    writeStoredJson(REVIEW_STORAGE_KEY, next);
    return { item, mocked: true };
  }
}

export async function listDefenseSessions(): Promise<{ items: DefenseSessionRecord[]; mocked: boolean }> {
  try {
    const data = await requestJson<ApiDefenseSessionRecord[]>("/api/v1/defense-sessions");
    return { items: data.map(mapDefenseSession), mocked: false };
  } catch {
    return { items: readMockDefenseSessions(), mocked: true };
  }
}

export async function loadAssessmentFeed(): Promise<AssessmentFeed> {
  const [reviews, defenses] = await Promise.all([listReviewAttempts(), listDefenseSessions()]);
  return {
    reviewAttempts: reviews.items,
    defenseSessions: defenses.items,
    mocked: reviews.mocked || defenses.mocked,
  };
}
