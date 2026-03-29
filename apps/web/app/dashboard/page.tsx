import Link from "next/link";

import { getDashboardData, getTmuxSessions } from "@/lib/api";
import type { ModuleItem, TrackItem } from "@/lib/api";
import { TmuxSessions } from "@/app/components/TmuxSessions";

/* ------------------------------------------------------------------ */
/*  Prerequisite map (same as module detail page)                      */
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
/*  Skill state derivation                                             */
/* ------------------------------------------------------------------ */

type SkillState = "done" | "in_progress" | "todo";
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

function deriveSkillState(
  skill: string,
  completedItems: string[],
  inProgressItems: string[],
): SkillState {
  const lower = skill.toLowerCase();
  if (completedItems.some((c) => c.toLowerCase().includes(lower))) return "done";
  if (inProgressItems.some((c) => c.toLowerCase().includes(lower))) return "in_progress";
  return "todo";
}

function stateLabel(state: ModuleState): string {
  switch (state) {
    case "done": return "Completed";
    case "in_progress": return "In progress";
    case "todo": return "Not started";
  }
}

/* ------------------------------------------------------------------ */
/*  Stat helpers                                                       */
/* ------------------------------------------------------------------ */

type TrackStats = {
  total: number;
  done: number;
  inProgress: number;
};

function computeTrackStats(
  track: TrackItem,
  activeTrack: string,
  activeModule: string,
): TrackStats {
  let done = 0;
  let inProgress = 0;
  for (const mod of track.modules) {
    const state = deriveModuleState(mod.id, track.id, activeTrack, activeModule, track.modules);
    if (state === "done") done++;
    else if (state === "in_progress") inProgress++;
  }
  return { total: track.modules.length, done, inProgress };
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default async function DashboardPage() {
  const [data, tmuxData] = await Promise.all([getDashboardData(), getTmuxSessions()]);
  const { curriculum, progression } = data;

  const activeTrack = progression.learning_plan?.active_course ?? "shell";
  const activeModule = progression.learning_plan?.active_module ?? "";
  const completedItems = progression.progress?.completed ?? [];
  const inProgressItems = progression.progress?.in_progress ?? [];

  const totalSkills = curriculum.tracks.reduce(
    (sum, t) => sum + t.modules.reduce((s, m) => s + m.skills.length, 0),
    0,
  );
  const totalModules = curriculum.tracks.reduce((sum, t) => sum + t.modules.length, 0);

  return (
    <main className="page-shell dashboard-page">
      {/* Hero */}
      <section className="dashboard-hero panel">
        <div className="dashboard-hero-copy">
          <p className="eyebrow">Skill Dashboard</p>
          <h1>Competency map across all tracks</h1>
          <p className="lead">
            Visual overview of every skill in the curriculum, organized by track and module.
            Each node reflects your current progression state.
          </p>
        </div>
        <div className="dashboard-hero-stats">
          <div className="metric-card">
            <span>Tracks</span>
            <strong>{curriculum.tracks.length}</strong>
          </div>
          <div className="metric-card">
            <span>Modules</span>
            <strong>{totalModules}</strong>
          </div>
          <div className="metric-card">
            <span>Skills</span>
            <strong>{totalSkills}</strong>
          </div>
          <div className="metric-card">
            <span>Active</span>
            <strong>{activeTrack}</strong>
          </div>
        </div>
      </section>

      {/* Main body: skill graph + sidebar */}
      <section className="section split dashboard-body">
        <div className="dashboard-main">
          {curriculum.tracks.map((track) => {
            const stats = computeTrackStats(track, activeTrack, activeModule);
            const pct = stats.total > 0 ? Math.round((stats.done / stats.total) * 100) : 0;

            return (
              <article key={track.id} className="panel dashboard-track">
                <div className="dashboard-track-header">
                  <div>
                    <p className="eyebrow">{track.id} track</p>
                    <h2>{track.title}</h2>
                    <p className="muted">{track.summary}</p>
                  </div>
                  <div className="dashboard-track-progress">
                    <span className="dashboard-track-pct">{pct}%</span>
                    <div className="progress-bar">
                      <div
                        className="progress-bar-fill"
                        style={{
                          width: `${pct}%`,
                          background: `var(--${track.id === "python_ai" ? "python" : track.id})`,
                        }}
                      />
                    </div>
                    <span className="muted">
                      {stats.done}/{stats.total} modules
                    </span>
                  </div>
                </div>

                <div className="skill-graph">
                  {track.modules.map((mod) => {
                    const modState = deriveModuleState(
                      mod.id, track.id, activeTrack, activeModule, track.modules,
                    );
                    const prereqs = mod.prerequisites ?? PREREQUISITE_MAP[mod.id] ?? [];

                    return (
                      <div key={mod.id} className="skill-graph-node-group">
                        {/* Module header node */}
                        <Link
                          href={`/modules/${mod.id}`}
                          className={`skill-graph-module skill-graph-module--${modState}`}
                        >
                          <div className="skill-graph-module-header">
                            <span className={`skill-graph-dot skill-graph-dot--${modState}`} />
                            <strong>{mod.title}</strong>
                            <span className="skill-graph-state">{stateLabel(modState)}</span>
                          </div>
                          {prereqs.length > 0 && (
                            <div className="skill-graph-prereqs">
                              {prereqs.map((p) => (
                                <span key={p} className="skill-graph-prereq-tag">{p}</span>
                              ))}
                            </div>
                          )}
                        </Link>

                        {/* Skill nodes under this module */}
                        <div className="skill-graph-skills">
                          {mod.skills.map((skill) => {
                            const ss = modState === "todo"
                              ? "todo"
                              : deriveSkillState(skill, completedItems, inProgressItems);
                            return (
                              <div
                                key={skill}
                                className={`skill-graph-skill skill-graph-skill--${ss}`}
                              >
                                <span className={`skill-graph-skill-dot skill-graph-skill-dot--${ss}`} />
                                <span>{skill}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </article>
            );
          })}
        </div>

        {/* Sidebar: tmux sessions + legend */}
        <aside className="dashboard-sidebar">
          <article className="panel">
            <p className="eyebrow">Agent Sessions</p>
            <h2>Tmux workspace</h2>
            <TmuxSessions sessions={tmuxData.sessions} />
          </article>

          <article className="panel">
            <p className="eyebrow">Legend</p>
            <h2>Skill states</h2>
            <div className="dashboard-legend">
              <div className="dashboard-legend-item">
                <span className="skill-graph-dot skill-graph-dot--done" />
                <span>Completed</span>
              </div>
              <div className="dashboard-legend-item">
                <span className="skill-graph-dot skill-graph-dot--in_progress" />
                <span>In progress</span>
              </div>
              <div className="dashboard-legend-item">
                <span className="skill-graph-dot skill-graph-dot--todo" />
                <span>Not started</span>
              </div>
            </div>
          </article>

          <article className="panel">
            <p className="eyebrow">Current focus</p>
            <h2>Active session</h2>
            <p>{progression.progress?.current_exercise ?? "No active exercise"}</p>
            <p className="muted">{progression.progress?.current_step ?? "No current step"}</p>
            {progression.next_command && (
              <div className="dashboard-next-cmd">
                <span className="muted">Next command</span>
                <code className="prog-code">{progression.next_command}</code>
              </div>
            )}
          </article>
        </aside>
      </section>
    </main>
  );
}
