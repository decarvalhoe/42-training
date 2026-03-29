import type { ReactNode } from "react";
import Link from "next/link";

import { getDashboardData } from "@/lib/api";
import type { ModuleItem } from "@/lib/api";

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

const TRACK_CLASS: Record<string, string> = {
  shell: "track-shell",
  c: "track-c",
  python_ai: "track-python",
};

const TRACK_COLORS: Record<string, string> = {
  shell: "var(--shell)",
  c: "var(--c)",
  python_ai: "var(--python)",
};

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default async function ProgressionPage() {
  const data = await getDashboardData();
  const { curriculum, progression } = data;

  const activeTrack = progression.learning_plan?.active_course ?? "shell";
  const activeModule = progression.learning_plan?.active_module ?? "";

  /* Build a flat list of all modules with their state and track */
  type ModuleWithContext = {
    module: ModuleItem;
    trackId: string;
    trackTitle: string;
    state: ModuleState;
  };

  const allModules: ModuleWithContext[] = [];

  for (const track of curriculum.tracks) {
    for (const mod of track.modules) {
      const state = deriveModuleState(mod.id, track.id, activeTrack, activeModule, track.modules);
      allModules.push({
        module: mod,
        trackId: track.id,
        trackTitle: track.title,
        state,
      });
    }
  }

  const doneModules = allModules.filter((m) => m.state === "done");
  const inProgressModules = allModules.filter((m) => m.state === "in_progress");
  const todoModules = allModules.filter((m) => m.state === "todo");

  /* Per-track completion stats */
  type TrackStats = {
    id: string;
    title: string;
    total: number;
    done: number;
    percent: number;
  };

  const trackStats: TrackStats[] = curriculum.tracks.map((track) => {
    const trackModules = allModules.filter((m) => m.trackId === track.id);
    const done = trackModules.filter((m) => m.state === "done").length;
    const total = trackModules.length;
    return {
      id: track.id,
      title: track.title,
      total,
      done,
      percent: total > 0 ? Math.round((done / total) * 100) : 0,
    };
  });

  const totalModules = allModules.length;
  const totalDone = doneModules.length;
  const globalPercent = totalModules > 0 ? Math.round((totalDone / totalModules) * 100) : 0;

  /* Next recommended action: first todo module whose prerequisites are all done */
  function prerequisitesMet(moduleId: string): boolean {
    const prereqs = PREREQUISITE_MAP[moduleId] ?? [];
    return prereqs.every((pid) => {
      const entry = allModules.find((m) => m.module.id === pid);
      return entry?.state === "done";
    });
  }

  const nextRecommended = todoModules.find((m) => prerequisitesMet(m.module.id));

  return (
    <main className="page-shell">
      {/* Breadcrumb */}
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link href="/">Dashboard</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Progression</span>
      </nav>

      {/* Header */}
      <section className="progression-hero panel">
        <p className="eyebrow">Personal progression</p>
        <h1>Your learning journey</h1>
        <p className="lead">
          Track your progress across Shell, C and Python + AI.
          Complete prerequisites to unlock the next modules.
        </p>

        {/* Global stats */}
        <div className="prog-stats-grid">
          <div className="metric-card">
            <span>Overall</span>
            <strong>{globalPercent}%</strong>
            <p className="muted">{totalDone} / {totalModules} modules</p>
          </div>
          {trackStats.map((ts) => (
            <div key={ts.id} className={`metric-card ${TRACK_CLASS[ts.id] ?? ""}`}>
              <span>{ts.title}</span>
              <strong>{ts.percent}%</strong>
              <div className="progress-bar">
                <div
                  className="progress-bar-fill"
                  style={{ "--bar-width": `${ts.percent}%` } as React.CSSProperties}
                />
              </div>
              <p className="muted">{ts.done} / {ts.total} modules</p>
            </div>
          ))}
        </div>
      </section>

      {/* Next recommended action */}
      {nextRecommended && (
        <section className="panel prog-next-action">
          <p className="eyebrow">Next recommended action</p>
          <div className="prog-next-content">
            <div>
              <h2>{nextRecommended.module.title}</h2>
              <p className="muted">
                {nextRecommended.trackTitle} &middot; {nextRecommended.module.phase}
              </p>
              <p>{nextRecommended.module.deliverable}</p>
            </div>
            <Link
              href={`/modules/${nextRecommended.module.id}`}
              className="action-btn"
            >
              Start module
            </Link>
          </div>
        </section>
      )}

      {/* Two-column body: in-progress + backlog */}
      <section className="section split prog-body">
        {/* In-progress checklist */}
        <article className="panel">
          <p className="eyebrow">In progress</p>
          <h2>Active modules ({inProgressModules.length})</h2>
          {inProgressModules.length === 0 ? (
            <p className="muted">No modules in progress.</p>
          ) : (
            <div className="prog-checklist">
              {inProgressModules.map((m) => (
                <Link
                  key={m.module.id}
                  href={`/modules/${m.module.id}`}
                  className="prog-checklist-item prog-checklist-item--active"
                >
                  <span className="prog-check prog-check--in_progress" />
                  <div className="prog-checklist-info">
                    <strong>{m.module.title}</strong>
                    <span className="muted">{m.trackTitle}</span>
                  </div>
                  <Pill variant="in_progress">{m.module.phase}</Pill>
                </Link>
              ))}
            </div>
          )}

          {/* Completed checklist */}
          {doneModules.length > 0 && (
            <>
              <h2 className="section-heading-spaced">Completed ({doneModules.length})</h2>
              <div className="prog-checklist">
                {doneModules.map((m) => (
                  <Link
                    key={m.module.id}
                    href={`/modules/${m.module.id}`}
                    className="prog-checklist-item prog-checklist-item--done"
                  >
                    <span className="prog-check prog-check--done">{"\u2713"}</span>
                    <div className="prog-checklist-info">
                      <strong>{m.module.title}</strong>
                      <span className="muted">{m.trackTitle}</span>
                    </div>
                    <Pill variant="done">{stateLabel("done")}</Pill>
                  </Link>
                ))}
              </div>
            </>
          )}
        </article>

        {/* Backlog */}
        <article className="panel">
          <p className="eyebrow">Backlog</p>
          <h2>Upcoming modules ({todoModules.length})</h2>
          {todoModules.length === 0 ? (
            <p className="muted">All modules started or completed.</p>
          ) : (
            <div className="prog-checklist">
              {todoModules.map((m) => {
                const met = prerequisitesMet(m.module.id);
                return (
                  <Link
                    key={m.module.id}
                    href={`/modules/${m.module.id}`}
                    className={`prog-checklist-item ${met ? "prog-checklist-item--ready" : "prog-checklist-item--blocked"}`}
                  >
                    <span className={`prog-check ${met ? "prog-check--ready" : "prog-check--blocked"}`}>
                      {met ? "\u25CB" : "\u2022"}
                    </span>
                    <div className="prog-checklist-info">
                      <strong>{m.module.title}</strong>
                      <span className="muted">{m.trackTitle}</span>
                      {!met && (
                        <span className="prog-blocked-label">
                          Requires: {(PREREQUISITE_MAP[m.module.id] ?? []).join(", ")}
                        </span>
                      )}
                    </div>
                    <Pill>{m.module.phase}</Pill>
                  </Link>
                );
              })}
            </div>
          )}
        </article>
      </section>

      {/* Current session detail */}
      {progression.progress?.current_exercise && (
        <section className="panel">
          <p className="eyebrow">Current session</p>
          <h2>{progression.progress.current_exercise}</h2>
          <p>{progression.progress.current_step ?? ""}</p>
          {progression.next_command && (
            <p className="section-note-spaced">
              Next command: <code className="prog-code">{progression.next_command}</code>
            </p>
          )}
        </section>
      )}
    </main>
  );
}
