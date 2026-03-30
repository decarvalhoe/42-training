"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { loadAssessmentFeed, type DefenseSessionRecord, type ReviewAttemptRecord } from "@/services/reviewEvidence";
import {
  GuidedActionButton,
  GuidedBadge,
  GuidedEmptyState,
  GuidedField,
  GuidedPanel,
  GuidedSelect,
  GuidedSidebarSection,
} from "@/app/components/GuidedSurface";

type ModuleOption = {
  id: string;
  title: string;
  trackId: string;
  trackTitle: string;
};

type Props = {
  modules: ModuleOption[];
};

type ArtifactItem = {
  id: string;
  source: "review" | "defense";
  moduleId: string;
  title: string;
  kind: string;
  content: string;
  actor: string;
  createdAt: string;
};

function moduleLabel(moduleId: string, modules: ModuleOption[]) {
  const module = modules.find((item) => item.id === moduleId);
  return module ? `${module.trackTitle} — ${module.title}` : moduleId;
}

function formatTimestamp(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function flattenReviewArtifacts(items: ReviewAttemptRecord[]): ArtifactItem[] {
  return items.flatMap((item, index) =>
    item.evidenceArtifacts.map((artifact, artifactIndex) => ({
      id: `${item.id}-${artifactIndex}-${index}`,
      source: "review" as const,
      moduleId: item.moduleId,
      title: artifact.label,
      kind: artifact.kind,
      content: artifact.content,
      actor: item.reviewerId,
      createdAt: item.createdAt,
    })),
  );
}

function flattenDefenseArtifacts(items: DefenseSessionRecord[]): ArtifactItem[] {
  return items.flatMap((item, index) =>
    item.evidenceArtifacts.map((artifact, artifactIndex) => ({
      id: `${item.sessionId}-${artifactIndex}-${index}`,
      source: "defense" as const,
      moduleId: item.moduleId,
      title: artifact.label,
      kind: artifact.kind,
      content: artifact.content,
      actor: item.learnerId ?? "anonymous",
      createdAt: item.createdAt,
    })),
  );
}

export default function EvidenceClient({ modules }: Props) {
  const [reviewAttempts, setReviewAttempts] = useState<ReviewAttemptRecord[]>([]);
  const [defenseSessions, setDefenseSessions] = useState<DefenseSessionRecord[]>([]);
  const [selectedModule, setSelectedModule] = useState<string>("all");
  const [loadingState, setLoadingState] = useState<"loading" | "ready" | "error">("loading");
  const [mocked, setMocked] = useState(false);

  const loadFeed = useCallback(async (cancelledRef?: { current: boolean }) => {
    setLoadingState("loading");

    try {
      const data = await loadAssessmentFeed();
      if (cancelledRef?.current) {
        return;
      }
      setReviewAttempts(data.reviewAttempts);
      setDefenseSessions(data.defenseSessions);
      setMocked(data.mocked);
      setLoadingState("ready");
    } catch {
      if (!cancelledRef?.current) {
        setLoadingState("error");
      }
    }
  }, []);

  useEffect(() => {
    const cancelledRef = { current: false };
    void loadFeed(cancelledRef);

    return () => {
      cancelledRef.current = true;
    };
  }, [loadFeed]);

  const artifacts = useMemo(() => {
    const combined = [...flattenReviewArtifacts(reviewAttempts), ...flattenDefenseArtifacts(defenseSessions)].sort((a, b) =>
      b.createdAt.localeCompare(a.createdAt),
    );

    if (selectedModule === "all") {
      return combined;
    }

    return combined.filter((item) => item.moduleId === selectedModule);
  }, [defenseSessions, reviewAttempts, selectedModule]);

  if (loadingState === "loading") {
    return <GuidedEmptyState title="Loading evidence feed..." body="Review and defense artifacts are being consolidated into the evidence workspace." />;
  }

  if (loadingState === "error") {
    return (
      <GuidedEmptyState
        title="Evidence feed unavailable"
        body="The page could not load review or defense artifacts. Retry once the assessment endpoints are reachable again."
        action={<GuidedActionButton onClick={() => void loadFeed()}>Retry</GuidedActionButton>}
      />
    );
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
      <div className="grid gap-4">
        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Evidence workspace">
            <h1 className="font-mono text-2xl font-semibold uppercase tracking-[0.08em] text-[var(--shell-ink)]">
              Linked artifacts
            </h1>
            <p className="text-sm leading-7 text-[var(--shell-muted)]">
              Keep the traces that prove how the learner reasoned, not just the final answer.
            </p>
            <div className="flex flex-wrap gap-2 pt-2">
              <GuidedBadge tone={mocked ? "warning" : "success"}>
                {mocked ? "demo mode" : "api live"}
              </GuidedBadge>
            </div>
          </GuidedSidebarSection>
        </GuidedPanel>

        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Summary">
            <div className="grid gap-3">
              <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
                <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Review attempts</p>
                <p className="mt-3 font-mono text-xl font-semibold text-[var(--shell-ink)]">{reviewAttempts.length}</p>
              </div>
              <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
                <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Defense sessions</p>
                <p className="mt-3 font-mono text-xl font-semibold text-[var(--shell-ink)]">{defenseSessions.length}</p>
              </div>
              <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
                <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Visible artifacts</p>
                <p className="mt-3 font-mono text-xl font-semibold text-[var(--shell-ink)]">{artifacts.length}</p>
              </div>
            </div>
          </GuidedSidebarSection>
        </GuidedPanel>

        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Filter">
            <GuidedField label="Module">
              <GuidedSelect value={selectedModule} onChange={(event) => setSelectedModule(event.target.value)}>
                <option value="all">All modules</option>
                {modules.map((module) => (
                  <option key={module.id} value={module.id}>
                    {module.trackTitle} — {module.title}
                  </option>
                ))}
              </GuidedSelect>
            </GuidedField>
          </GuidedSidebarSection>
        </GuidedPanel>
      </div>

      <GuidedPanel className="px-6 py-6">
        <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
          evidence // consolidated feed
        </p>
        <h2 className="mt-4 font-mono text-2xl font-semibold uppercase tracking-[0.08em] text-[var(--shell-ink)]">
          Notes, outputs and defense traces
        </h2>

        <div className="mt-6 grid gap-4">
          {artifacts.length === 0 ? (
            <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-5 py-5">
              <h3 className="font-mono text-sm font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                No artifacts for this filter
              </h3>
              <p className="mt-3 text-sm leading-7 text-[var(--shell-muted)]">
                Submit a guided review or finish a defense session with evidence to populate this view.
              </p>
            </div>
          ) : (
            artifacts.map((artifact) => (
              <article key={artifact.id} className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-5 py-5">
                <div className="flex flex-wrap items-center gap-2">
                  <GuidedBadge tone={artifact.source === "defense" ? "warning" : "success"}>{artifact.source}</GuidedBadge>
                  <GuidedBadge>{artifact.kind}</GuidedBadge>
                  <GuidedBadge>{artifact.actor}</GuidedBadge>
                </div>
                <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h3 className="font-mono text-sm font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                      {artifact.title}
                    </h3>
                    <p className="mt-2 text-sm leading-6 text-[var(--shell-muted)]">
                      {moduleLabel(artifact.moduleId, modules)}
                    </p>
                  </div>
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-dim)]">
                    {formatTimestamp(artifact.createdAt)}
                  </span>
                </div>
                <pre className="mt-4 overflow-x-auto border border-[var(--shell-border)] bg-[var(--shell-sidebar)] px-4 py-4 font-mono text-[12px] leading-6 text-[var(--shell-ink)]">
                  {artifact.content}
                </pre>
              </article>
            ))
          )}
        </div>
      </GuidedPanel>
    </div>
  );
}
