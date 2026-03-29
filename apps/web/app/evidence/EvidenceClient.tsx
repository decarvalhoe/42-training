"use client";

import { useEffect, useMemo, useState } from "react";

import { loadAssessmentFeed, type DefenseSessionRecord, type ReviewAttemptRecord } from "@/services/reviewEvidence";

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
    }))
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
    }))
  );
}

export default function EvidenceClient({ modules }: Props) {
  const [reviewAttempts, setReviewAttempts] = useState<ReviewAttemptRecord[]>([]);
  const [defenseSessions, setDefenseSessions] = useState<DefenseSessionRecord[]>([]);
  const [selectedModule, setSelectedModule] = useState<string>("all");
  const [loadingState, setLoadingState] = useState<"loading" | "ready" | "error">("loading");
  const [mocked, setMocked] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadFeed() {
      try {
        const data = await loadAssessmentFeed();
        if (cancelled) {
          return;
        }
        setReviewAttempts(data.reviewAttempts);
        setDefenseSessions(data.defenseSessions);
        setMocked(data.mocked);
        setLoadingState("ready");
      } catch {
        if (!cancelled) {
          setLoadingState("error");
        }
      }
    }

    void loadFeed();

    return () => {
      cancelled = true;
    };
  }, []);

  const artifacts = useMemo(() => {
    const combined = [...flattenReviewArtifacts(reviewAttempts), ...flattenDefenseArtifacts(defenseSessions)].sort((a, b) =>
      b.createdAt.localeCompare(a.createdAt)
    );

    if (selectedModule === "all") {
      return combined;
    }

    return combined.filter((item) => item.moduleId === selectedModule);
  }, [defenseSessions, reviewAttempts, selectedModule]);

  if (loadingState === "loading") {
    return (
      <section className="panel evidence-shell">
        <h2>Loading evidence feed...</h2>
      </section>
    );
  }

  if (loadingState === "error") {
    return (
      <section className="panel evidence-shell">
        <h2>Evidence feed unavailable</h2>
        <p className="muted">The page could not load review or defense artifacts.</p>
      </section>
    );
  }

  return (
    <section className="evidence-shell">
      <article className="panel evidence-summary">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Consolidated feed</p>
            <h2>Artifact overview</h2>
          </div>
          <span className="pill">{mocked ? "Demo mode" : "API live"}</span>
        </div>

        <div className="hero-grid">
          <div className="metric-card">
            <span>Review attempts</span>
            <strong>{reviewAttempts.length}</strong>
          </div>
          <div className="metric-card">
            <span>Defense sessions</span>
            <strong>{defenseSessions.length}</strong>
          </div>
          <div className="metric-card">
            <span>Visible artifacts</span>
            <strong>{artifacts.length}</strong>
          </div>
          <div className="metric-card">
            <span>Current filter</span>
            <strong>{selectedModule === "all" ? "All modules" : moduleLabel(selectedModule, modules)}</strong>
          </div>
        </div>

        <label className="defense-field">
          <span>Filter by module</span>
          <select value={selectedModule} onChange={(event) => setSelectedModule(event.target.value)}>
            <option value="all">All modules</option>
            {modules.map((module) => (
              <option key={module.id} value={module.id}>
                {module.trackTitle} — {module.title}
              </option>
            ))}
          </select>
        </label>
      </article>

      <article className="panel evidence-list-panel">
        <p className="eyebrow">Artifacts</p>
        <h2>Notes, outputs and defense traces</h2>

        <div className="evidence-list">
          {artifacts.length === 0 ? (
            <article className="evidence-card">
              <h3>No artifacts for this filter</h3>
              <p className="muted">
                Submit a guided review or finish a defense session with evidence to populate this view.
              </p>
            </article>
          ) : (
            artifacts.map((artifact) => (
              <article key={artifact.id} className={`evidence-card evidence-card--${artifact.source}`}>
                <div className="card-topline">
                  <span>{artifact.source}</span>
                  <span>{formatTimestamp(artifact.createdAt)}</span>
                </div>
                <h3>{artifact.title}</h3>
                <p className="muted">{moduleLabel(artifact.moduleId, modules)}</p>
                <div className="evidence-meta">
                  <span>{artifact.kind}</span>
                  <span>{artifact.actor}</span>
                </div>
                <pre className="evidence-content">{artifact.content}</pre>
              </article>
            ))
          )}
        </div>
      </article>
    </section>
  );
}
