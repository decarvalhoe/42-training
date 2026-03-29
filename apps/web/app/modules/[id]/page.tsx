import type { ReactNode } from "react";
import Link from "next/link";

import { getDashboardData } from "@/lib/api";
import type { ModuleItem } from "@/lib/api";
import { SourcePolicyBadge } from "@/app/components/SourcePolicyBadge";
import { TabbedTerminalViewer } from "@/app/components/TabbedTerminalViewer";
import { isDisplayableSourcePolicyTier } from "@/lib/sourcePolicy";

/* ------------------------------------------------------------------ */
/*  Static prerequisite map (from documented dependency graph)         */
/* ------------------------------------------------------------------ */

const PREREQUISITE_MAP: Record<string, string[]> = {
  "shell-basics": [],
  "shell-streams": ["shell-basics"],
  "shell-permissions": ["shell-basics"],
  "shell-tooling": ["shell-streams", "shell-permissions"],
  "c-basics": ["shell-basics"],
  "c-memory": ["c-basics"],
  "c-build-debug": ["c-basics", "shell-streams"],
  "c-libft-pushswap-bridge": ["c-memory", "c-build-debug"],
  "python-basics": ["shell-basics"],
  "python-oop-scripting": ["python-basics"],
  "ai-rag-agents": ["python-oop-scripting"],
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function Pill({ children, variant }: { children: ReactNode; variant?: string }) {
  const cls = variant ? `pill pill--${variant}` : "pill";
  return <span className={cls}>{children}</span>;
}

type ModuleState = "done" | "in_progress" | "todo";

function deriveModuleState(
  moduleId: string,
  trackId: string,
  activeTrack: string,
  activeModule: string,
  modules: ModuleItem[],
): ModuleState {
  if (trackId !== activeTrack) return "todo";
  if (moduleId === activeModule) return "in_progress";
  const activeIndex = modules.findIndex((m) => m.id === activeModule);
  const currentIndex = modules.findIndex((m) => m.id === moduleId);
  if (activeIndex === -1) return "todo";
  return currentIndex < activeIndex ? "done" : "todo";
}

function stateLabel(state: ModuleState): string {
  switch (state) {
    case "done":
      return "Completed";
    case "in_progress":
      return "In progress";
    case "todo":
      return "Not started";
  }
}

function actionLabel(state: ModuleState): string {
  switch (state) {
    case "done":
      return "Review module";
    case "in_progress":
      return "Continue";
    case "todo":
      return "Start module";
  }
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default async function ModuleDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const data = await getDashboardData();
  const { curriculum, progression } = data;

  const activeTrack = progression.learning_plan?.active_course ?? "shell";
  const activeModule = progression.learning_plan?.active_module ?? "";

  /* Find the module and its parent track */
  let foundModule: ModuleItem | undefined;
  let foundTrackId = "";
  let trackModules: ModuleItem[] = [];

  for (const track of curriculum.tracks) {
    const mod = track.modules.find((m) => m.id === id);
    if (mod) {
      foundModule = mod;
      foundTrackId = track.id;
      trackModules = track.modules;
      break;
    }
  }

  if (!foundModule) {
    return (
      <main className="page-shell">
        <section className="panel not-found-panel">
          <h1>Module not found</h1>
          <p className="muted">No module with id &ldquo;{id}&rdquo; exists in the curriculum.</p>
          <Link href="/" className="action-btn not-found-action">
            Back to dashboard
          </Link>
        </section>
      </main>
    );
  }

  const state = deriveModuleState(id, foundTrackId, activeTrack, activeModule, trackModules);
  const prerequisites = foundModule.prerequisites ?? PREREQUISITE_MAP[id] ?? [];

  /* Derive prerequisite satisfaction */
  const prereqStatus = prerequisites.map((prereqId) => {
    const prereqState = deriveModuleState(prereqId, foundTrackId, activeTrack, activeModule, trackModules);
    /* Cross-track prereqs: check all tracks */
    let resolved = prereqState === "done";
    if (!resolved) {
      for (const track of curriculum.tracks) {
        const prereqMod = track.modules.find((m) => m.id === prereqId);
        if (prereqMod) {
          const s = deriveModuleState(prereqId, track.id, activeTrack, activeModule, track.modules);
          resolved = s === "done";
          break;
        }
      }
    }
    return { id: prereqId, satisfied: resolved };
  });

  const allPrereqsMet = prereqStatus.every((p) => p.satisfied);

  /* Gather authorized resources (filter by source policy) */
  const moduleResources = foundModule.resources ?? [];
  const globalResources = curriculum.recommended_resources ?? [];
  const authorizedResources = [
    ...moduleResources.filter((r) => isDisplayableSourcePolicyTier(r.tier)),
    ...globalResources.filter((r) => isDisplayableSourcePolicyTier(r.tier)),
  ];

  /* Derive skill states from progression */
  const completedItems = progression.progress?.completed ?? [];
  const inProgressItems = progression.progress?.in_progress ?? [];

  function skillState(skill: string): "done" | "in_progress" | "todo" {
    const lower = skill.toLowerCase();
    if (completedItems.some((c) => c.toLowerCase().includes(lower))) return "done";
    if (inProgressItems.some((c) => c.toLowerCase().includes(lower))) return "in_progress";
    return "todo";
  }

  return (
    <main className="page-shell">
      {/* Breadcrumb */}
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link href="/">Dashboard</Link>
        <span className="breadcrumb-sep">/</span>
        <span>{foundTrackId}</span>
        <span className="breadcrumb-sep">/</span>
        <span>{foundModule.title}</span>
      </nav>

      {/* Header */}
      <section className="module-detail-hero panel">
        <div className="module-detail-topline">
          <Pill variant={state}>{stateLabel(state)}</Pill>
          <Pill>{foundModule.phase}</Pill>
          {foundModule.estimated_hours != null && (
            <span className="muted">{foundModule.estimated_hours}h estimated</span>
          )}
        </div>
        <h1>{foundModule.title}</h1>
        <p className="lead">{foundModule.deliverable}</p>

        <button
          className={`action-btn action-btn--${state}`}
          disabled={!allPrereqsMet && state === "todo"}
        >
          {!allPrereqsMet && state === "todo"
            ? "Prerequisites not met"
            : actionLabel(state)}
        </button>
      </section>

      {/* Two-column body */}
      <section className="section split module-detail-body">
        <div className="module-detail-main">
          {/* Objectives checklist */}
          {foundModule.objectives && foundModule.objectives.length > 0 && (
            <article className="panel">
              <p className="eyebrow">Objectives</p>
              <ul className="checklist">
                {foundModule.objectives.map((obj) => {
                  const done = completedItems.some((c) => c.toLowerCase().includes(obj.toLowerCase().split(" ")[0]));
                  return (
                    <li key={obj} className={`checklist-item${done ? " checklist-item--done" : ""}`}>
                      <span className="checklist-box">{done ? "\u2713" : "\u00A0"}</span>
                      <span>{obj}</span>
                    </li>
                  );
                })}
              </ul>
            </article>
          )}

          {/* Skills checklist */}
          <article className="panel">
            <p className="eyebrow">Skills</p>
            <h2>Competencies to acquire</h2>
            <ul className="checklist">
              {foundModule.skills.map((skill) => {
                const ss = state === "todo" ? "todo" : skillState(skill);
                return (
                  <li key={skill} className={`checklist-item${ss === "done" ? " checklist-item--done" : ""}`}>
                    <span className="checklist-box">{ss === "done" ? "\u2713" : "\u00A0"}</span>
                    <span>{skill}</span>
                    {ss === "in_progress" && <span className="checklist-badge">in progress</span>}
                  </li>
                );
              })}
            </ul>
          </article>

          {/* Exit criteria (if enriched data available) */}
          {foundModule.exit_criteria && foundModule.exit_criteria.length > 0 && (
            <article className="panel">
              <p className="eyebrow">Exit criteria</p>
              <ul className="objective-list">
                {foundModule.exit_criteria.map((ec) => (
                  <li key={ec}>{ec}</li>
                ))}
              </ul>
            </article>
          )}

          {/* Live terminal viewer (visible when module is active) */}
          {state === "in_progress" && (
            <TabbedTerminalViewer sessionPrefix="learn42" />
          )}
        </div>

        <aside className="module-detail-sidebar">
          {/* Prerequisites */}
          <article className="panel">
            <p className="eyebrow">Prerequisites</p>
            <h2>Required modules</h2>
            {prerequisites.length === 0 ? (
              <p className="muted">Entry point &mdash; no prerequisites.</p>
            ) : (
              <div className="prereq-list">
                {prereqStatus.map((p) => (
                  <div key={p.id} className={`prereq-item prereq-item--${p.satisfied ? "met" : "unmet"}`}>
                    <span className="prereq-indicator">{p.satisfied ? "\u2713" : "\u2717"}</span>
                    <span>{p.id}</span>
                  </div>
                ))}
              </div>
            )}
          </article>

          {/* Authorized resources */}
          <article className="panel">
            <p className="eyebrow">Authorized resources</p>
            <h2>Approved sources</h2>
            {authorizedResources.length === 0 ? (
              <p className="muted">No authorized resources available.</p>
            ) : (
              <div className="resource-list">
                {authorizedResources.map((r) => (
                  <div key={r.url} className="resource-item">
                    <a href={r.url} target="_blank" rel="noopener noreferrer">
                      {r.label}
                    </a>
                    <SourcePolicyBadge tier={r.tier} />
                  </div>
                ))}
              </div>
            )}
          </article>

          {/* Actions */}
          {state === "in_progress" && (
            <article className="panel module-actions">
              <p className="eyebrow">Actions</p>
              <div className="module-actions-list">
                <Link
                  href={`/mentor?module_id=${id}&track_id=${foundTrackId}`}
                  className="action-btn action-btn--secondary"
                >
                  Ask Mentor
                </Link>
                <Link
                  href={`/defense?track_id=${foundTrackId}&module_id=${id}`}
                  className="action-btn action-btn--in_progress"
                >
                  Start Defense
                </Link>
              </div>
            </article>
          )}
        </aside>
      </section>
    </main>
  );
}
