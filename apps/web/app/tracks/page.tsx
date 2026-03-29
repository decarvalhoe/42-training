import type { ReactNode } from "react";
import Link from "next/link";

import { getDashboardData } from "@/lib/api";
import type { ModuleItem, TrackItem } from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function Pill({ children }: { children: ReactNode }) {
  return <span className="pill">{children}</span>;
}

type ModuleState = "done" | "in_progress" | "locked" | "available";

function deriveModuleState(
  moduleId: string,
  trackId: string,
  activeTrack: string | undefined,
  activeModule: string | undefined,
  modules: ModuleItem[],
): ModuleState {
  if (trackId !== activeTrack) return "locked";
  if (moduleId === activeModule) return "in_progress";
  const activeIdx = modules.findIndex((m) => m.id === activeModule);
  const currentIdx = modules.findIndex((m) => m.id === moduleId);
  if (activeIdx === -1) return currentIdx === 0 ? "available" : "locked";
  if (currentIdx < activeIdx) return "done";
  if (currentIdx === activeIdx + 1) return "available";
  return "locked";
}

const PHASE_ORDER: Record<string, number> = {
  foundation: 0,
  practice: 1,
  core: 2,
  advanced: 3,
};

const STATE_ICON: Record<ModuleState, string> = {
  done: "◆",
  in_progress: "▶",
  available: "○",
  locked: "◇",
};

const TRACK_CLASS: Record<string, string> = {
  shell: "track-shell",
  c: "track-c",
  python_ai: "track-python",
};

/* ------------------------------------------------------------------ */
/*  Components                                                         */
/* ------------------------------------------------------------------ */

function TalentNode({
  mod,
  state,
  isLast,
}: {
  mod: ModuleItem;
  state: ModuleState;
  isLast: boolean;
}) {
  const phaseLabel = mod.phase.charAt(0).toUpperCase() + mod.phase.slice(1);

  return (
    <div className="talent-node-wrapper">
      <div className={`talent-node talent-node--${state}`}>
        <div className="talent-node-icon">
          {STATE_ICON[state]}
        </div>
        <div className="talent-node-body">
          <div className="talent-node-header">
            <Link href={`/modules/${mod.id}`} className="talent-node-title">
              {mod.title}
            </Link>
            <div className="talent-node-badges">
              <Pill>{phaseLabel}</Pill>
              {mod.estimated_hours != null && <Pill>{mod.estimated_hours}h</Pill>}
            </div>
          </div>
          <p className="talent-node-deliverable">{mod.deliverable}</p>
          <div className="stack-list">
            {mod.skills.slice(0, 5).map((skill) => (
              <Pill key={skill}>{skill}</Pill>
            ))}
            {mod.skills.length > 5 && <Pill>+{mod.skills.length - 5}</Pill>}
          </div>
          {(mod.objectives ?? []).length > 0 && (
            <ul className="talent-node-objectives">
              {(mod.objectives ?? []).slice(0, 3).map((obj) => (
                <li key={obj}>{obj}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
      {!isLast && (
        <div className="talent-edge" />
      )}
    </div>
  );
}

function TrackTree({
  track,
  activeTrack,
  activeModule,
}: {
  track: TrackItem;
  activeTrack: string | undefined;
  activeModule: string | undefined;
}) {
  const trackCls = TRACK_CLASS[track.id] ?? "";
  const phases = [...new Set(track.modules.map((m) => m.phase))].sort(
    (a, b) => (PHASE_ORDER[a] ?? 99) - (PHASE_ORDER[b] ?? 99),
  );

  const doneCount = track.modules.filter(
    (m) => deriveModuleState(m.id, track.id, activeTrack, activeModule, track.modules) === "done",
  ).length;
  const pct = track.modules.length > 0 ? Math.round((doneCount / track.modules.length) * 100) : 0;

  return (
    <article className={`talent-track ${trackCls}`}>
      <div className="talent-track-header">
        <div>
          <p className="eyebrow">{track.id}</p>
          <h2>{track.title}</h2>
          <p className="muted">{track.summary}</p>
        </div>
        <div className="talent-track-progress">
          <div className="talent-track-bar">
            <div
              className="talent-track-bar-fill"
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="muted">
            {doneCount}/{track.modules.length} modules &middot; {pct}%
          </span>
        </div>
      </div>

      {phases.map((phase) => {
        const phaseModules = track.modules.filter((m) => m.phase === phase);
        const phaseLabel = phase.charAt(0).toUpperCase() + phase.slice(1);
        return (
          <div key={phase} className="talent-phase">
            <div className="talent-phase-label">{phaseLabel}</div>
            <div className="talent-phase-nodes">
              {phaseModules.map((mod, idx) => {
                const state = deriveModuleState(mod.id, track.id, activeTrack, activeModule, track.modules);
                const isLastInPhase = idx === phaseModules.length - 1;
                const isLastPhase = phase === phases[phases.length - 1];
                return (
                  <TalentNode
                    key={mod.id}
                    mod={mod}
                    state={state}
                    isLast={isLastInPhase && isLastPhase}
                  />
                );
              })}
            </div>
          </div>
        );
      })}
    </article>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default async function TracksPage() {
  const data = await getDashboardData();
  const { curriculum, progression } = data;
  const activeTrack = progression.learning_plan?.active_course;
  const activeModule = progression.learning_plan?.active_module;

  const totalModules = curriculum.tracks.reduce((sum, t) => sum + t.modules.length, 0);

  return (
    <main className="page-shell">
      <nav className="breadcrumb">
        <Link href="/">Dashboard</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Tracks</span>
      </nav>

      <section className="panel talent-hero">
        <p className="eyebrow">Track Explorer</p>
        <h1>RPG Talent Tree</h1>
        <p className="lead">
          Navigate through {curriculum.tracks.length} tracks and {totalModules} modules.
          Complete modules to unlock the next tier and progress through foundation, practice, core and advanced phases.
        </p>
        <div className="talent-legend">
          <span><span className="talent-legend-icon status-completed">◆</span> Done</span>
          <span><span className="talent-legend-icon status-in-progress">▶</span> In progress</span>
          <span><span className="talent-legend-icon">○</span> Available</span>
          <span><span className="talent-legend-icon status-locked">◇</span> Locked</span>
        </div>
      </section>

      <section className="talent-trees">
        {curriculum.tracks.map((track) => (
          <TrackTree
            key={track.id}
            track={track}
            activeTrack={activeTrack}
            activeModule={activeModule}
          />
        ))}
      </section>
    </main>
  );
}
