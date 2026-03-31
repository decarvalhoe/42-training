import Link from "next/link";
import type { ReactNode } from "react";

import { DataSourceBadge } from "@/app/components/DataSourceBadge";
import { getAnalyticsData, getDashboardData, getTmuxSessions } from "@/lib/api";
import { countSkills, deriveModuleState, getLearningContext, getTrackTheme, summarizeSessions } from "@/lib/learner-progress";

import { SkillGraph, type GraphNodeData } from "./SkillGraph";

function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`border border-[var(--shell-border)] bg-[var(--shell-panel)] ${className}`}>
      {children}
    </section>
  );
}

function StatBlock({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="border-b border-[var(--shell-border)] px-4 py-4 last:border-b-0">
      <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">{label}</p>
      <p className="mt-3 font-mono text-2xl font-semibold text-[var(--shell-ink)]">{value}</p>
      <p className="mt-2 font-mono text-[10px] leading-5 text-[var(--shell-muted)]">{detail}</p>
    </div>
  );
}

export default async function DashboardPage() {
  const [data, analytics, tmuxData] = await Promise.all([
    getDashboardData(),
    getAnalyticsData(),
    getTmuxSessions(),
  ]);

  const { curriculum, progression } = data;
  const { activeTrack, activeModule, modules, trackStats } = getLearningContext(data);

  const completedModules = modules.filter((entry) => entry.state === "done").length;
  const totalModules = modules.length;
  const totalSkills = countSkills(curriculum.tracks);
  const tmuxSummary = summarizeSessions(tmuxData.sessions);

  // Build graph nodes from all tracks
  const graphNodes: GraphNodeData[] = curriculum.tracks.flatMap((track) =>
    track.modules.map((mod) => ({
      id: mod.id,
      title: mod.title,
      trackId: track.id,
      phase: mod.phase,
      skillCount: mod.skills.length,
      state: deriveModuleState(mod.id, track.id, activeTrack, activeModule, track.modules),
      prerequisites: (mod.prerequisites ?? []).filter((depId) =>
        curriculum.tracks.some((t) => t.modules.some((m) => m.id === depId)),
      ),
    })),
  );

  // Build themes map for the client component
  const themes: Record<string, { accent: string; surface: string }> = {};
  for (const track of curriculum.tracks) {
    const t = getTrackTheme(track.id);
    themes[track.id] = { accent: t.accent, surface: t.surface };
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[320px_minmax(0,1fr)]">
      {/* ---------- Sidebar stats ---------- */}
      <div className="grid gap-4">
        <Panel>
          <StatBlock
            label="Modules"
            value={`${completedModules}/${totalModules}`}
            detail={`${analytics.summary.module_completions} completion events recorded in analytics`}
          />
          <StatBlock
            label="Success rate"
            value={`${analytics.summary.checkpoint_success_rate}%`}
            detail="Checkpoint reliability across evaluated learner attempts"
          />
          <StatBlock
            label="Defense"
            value={`${analytics.summary.defenses_started}`}
            detail="Defense sessions started from the guided learner workflow"
          />
          <StatBlock
            label="Mentor queries"
            value={`${analytics.summary.mentor_queries}`}
            detail="AI mentor interactions preserved in the pedagogical event stream"
          />
          <StatBlock
            label="Skill coverage"
            value={`${totalSkills}`}
            detail={`${curriculum.tracks.length} tracks visible in the competency map`}
          />
        </Panel>

        <Panel className="px-5 py-5">
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Session health</p>
          <div className="mt-4 grid gap-3">
            <div className="flex items-center justify-between border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-3 font-mono text-[10px] uppercase tracking-[0.24em]">
              <span className="text-[var(--shell-muted)]">Live panes</span>
              <span className="text-[var(--shell-success)]">{tmuxSummary.active}</span>
            </div>
            <div className="flex items-center justify-between border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-3 font-mono text-[10px] uppercase tracking-[0.24em]">
              <span className="text-[var(--shell-muted)]">Idle panes</span>
              <span className="text-[var(--shell-ink)]">{tmuxSummary.idle}</span>
            </div>
            <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
              <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Current focus</p>
              <p className="mt-3 font-mono text-sm text-[var(--shell-ink)]">
                {progression.progress?.current_exercise ?? "No active exercise"}
              </p>
              <p className="mt-2 font-mono text-[10px] leading-5 text-[var(--shell-muted)]">
                {progression.progress?.current_step ?? progression.next_command ?? "No current step visible in the learner session."}
              </p>
            </div>
          </div>
        </Panel>
      </div>

      {/* ---------- Main content ---------- */}
      <div className="grid gap-4">
        <Panel className="px-6 py-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Dashboard</p>
              <h1 className="mt-3 font-mono text-2xl font-semibold uppercase tracking-[0.1em] text-[var(--shell-ink)]">
                Skill graph // learner state
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--shell-muted)]">
                Interactive competency map. Click any node to inspect prerequisites, skills and progress. Edges show dependency chains across the curriculum.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <DataSourceBadge sourceMode={data.sourceMode} />
              <Link
                href="/progression"
                className="inline-flex min-h-10 items-center justify-center border border-[var(--shell-border-strong)] px-4 py-2 font-mono text-[10px] uppercase tracking-[0.28em] text-[var(--shell-ink)] transition-colors hover:border-[var(--shell-success)] hover:text-[var(--shell-success)]"
              >
                Open progression
              </Link>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap items-center gap-6 font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
            <span className="flex items-center gap-2">
              <span className="inline-flex size-2 rounded-full bg-[var(--shell-success)]" />
              done
            </span>
            <span className="flex items-center gap-2">
              <span className="inline-flex size-2 rounded-full bg-[var(--shell-warning)]" />
              active
            </span>
            <span className="flex items-center gap-2">
              <span className="inline-flex size-2 rounded-full bg-[var(--shell-border-strong)]" />
              locked
            </span>
          </div>
        </Panel>

        {/* Interactive node graph */}
        <SkillGraph nodes={graphNodes} themes={themes} />

        {/* Per-track progress summary */}
        <Panel className="px-6 py-5">
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Track progress</p>
          <div className="mt-4 grid gap-3">
            {curriculum.tracks.map((track) => {
              const stats = trackStats.find((entry) => entry.id === track.id);
              const theme = getTrackTheme(track.id);
              return (
                <div key={track.id} className="flex items-center gap-4 border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="font-mono text-[9px] uppercase tracking-[0.28em]" style={{ color: theme.accent }}>
                      {theme.label} track
                    </p>
                    <p className="mt-1 truncate font-mono text-xs font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                      {track.title}
                    </p>
                  </div>
                  <div className="w-24">
                    <div className="h-1.5 overflow-hidden border border-[var(--shell-border)] bg-[var(--shell-panel)]">
                      <div className="h-full" style={{ width: `${stats?.percentComplete ?? 0}%`, backgroundColor: theme.accent }} />
                    </div>
                  </div>
                  <p className="font-mono text-sm font-semibold tabular-nums" style={{ color: theme.accent }}>
                    {stats?.percentComplete ?? 0}%
                  </p>
                </div>
              );
            })}
          </div>
        </Panel>
      </div>
    </div>
  );
}
