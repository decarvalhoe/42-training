import Link from "next/link";
import type { ReactNode } from "react";

import { DataSourceBadge } from "@/app/components/DataSourceBadge";
import { DashboardSidebar } from "@/app/dashboard/DashboardSidebar";
import { getAnalyticsData, getDashboardData, getTmuxSessions } from "@/lib/api";
import { countSkills, deriveModuleState, getLearningContext, getTrackTheme, summarizeSessions } from "@/lib/learner-progress";

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

function ModuleNode({
  href,
  title,
  phase,
  skillCount,
  state,
  accent,
  surface,
}: {
  href: string;
  title: string;
  phase: string;
  skillCount: number;
  state: "done" | "in_progress" | "todo";
  accent: string;
  surface: string;
}) {
  const visual =
    state === "done"
      ? {
          borderColor: accent,
          backgroundColor: surface,
          textColor: accent,
        }
      : state === "in_progress"
        ? {
            borderColor: "var(--shell-warning)",
            backgroundColor: "rgba(247, 190, 22, 0.08)",
            textColor: "var(--shell-warning)",
          }
        : {
            borderColor: "var(--shell-border)",
            backgroundColor: "rgba(45, 47, 54, 0.15)",
            textColor: "var(--shell-dim)",
          };

  const connectorColor = state === "todo" ? "var(--shell-border)" : accent;
  const phaseLabel = state === "in_progress" ? "active" : state === "done" ? "done" : phase;

  return (
    <div className="flex min-w-[240px] items-center gap-3">
      <Link
        href={href}
        className="flex min-h-[120px] min-w-[180px] flex-col justify-between border px-4 py-4 transition-colors hover:border-[var(--shell-success)]"
        style={{ borderColor: visual.borderColor, backgroundColor: visual.backgroundColor }}
      >
        <div className="flex items-start justify-between gap-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.24em]" style={{ color: visual.textColor }}>
            {phaseLabel}
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
            {skillCount} skills
          </span>
        </div>
        <h3 className="mt-6 font-mono text-sm font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
          {title}
        </h3>
      </Link>
      <div className="h-px min-w-8 flex-1 border-t border-dashed" style={{ borderColor: connectorColor }} />
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
  const orderedTracks = [...curriculum.tracks].sort((left, right) => {
    if (left.id === activeTrack) {
      return -1;
    }
    if (right.id === activeTrack) {
      return 1;
    }
    return 0;
  });

  const completedModules = modules.filter((entry) => entry.state === "done").length;
  const totalModules = modules.length;
  const totalSkills = countSkills(curriculum.tracks);
  const tmuxSummary = summarizeSessions(tmuxData.sessions);

  return (
    <>
      <DashboardSidebar
        completedModules={completedModules}
        totalModules={totalModules}
        completionEvents={analytics.summary.module_completions}
        successRate={analytics.summary.checkpoint_success_rate}
        defensesStarted={analytics.summary.defenses_started}
        mentorQueries={analytics.summary.mentor_queries}
        totalSkills={totalSkills}
        trackCount={curriculum.tracks.length}
        activePanes={tmuxSummary.active}
        idlePanes={tmuxSummary.idle}
        currentExercise={progression.progress?.current_exercise ?? null}
        currentStep={progression.progress?.current_step ?? progression.next_command ?? null}
      />
      <div className="grid gap-4">
        <Panel className="px-6 py-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Dashboard</p>
              <h1 className="mt-3 font-mono text-2xl font-semibold uppercase tracking-[0.1em] text-[var(--shell-ink)]">
                Skill graph // learner state
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-[var(--shell-muted)]">
                This surface is now dedicated to the competency map. It keeps the cross-track graph readable and pushes curriculum detail back into track and module views.
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

        <Panel className="px-6 py-6">
          <div className="grid gap-6">
            {orderedTracks.map((track) => {
              const stats = trackStats.find((entry) => entry.id === track.id);
              const theme = getTrackTheme(track.id);

              return (
                <section key={track.id} className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-5 py-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="font-mono text-[9px] uppercase tracking-[0.28em]" style={{ color: theme.accent }}>
                        {theme.label} track
                      </p>
                      <h2 className="mt-3 font-mono text-lg font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                        {track.title}
                      </h2>
                      <p className="mt-3 max-w-2xl text-sm leading-6 text-[var(--shell-muted)]">{track.summary}</p>
                    </div>
                    <div className="min-w-[180px]">
                      <p className="font-mono text-right text-xl font-semibold" style={{ color: theme.accent }}>
                        {stats?.percentComplete ?? 0}%
                      </p>
                      <div className="mt-3 h-2 overflow-hidden border border-[var(--shell-border)] bg-[var(--shell-panel)]">
                        <div
                          className="h-full"
                          style={{ width: `${stats?.percentComplete ?? 0}%`, backgroundColor: theme.accent }}
                        />
                      </div>
                      <p className="mt-3 text-right font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
                        {stats?.completedModules ?? 0}/{stats?.totalModules ?? track.modules.length} modules
                      </p>
                    </div>
                  </div>

                  <div className="mt-6 overflow-x-auto pb-2">
                    <div className="flex min-w-max items-center">
                      {track.modules.map((module, index) => {
                        const state = deriveModuleState(module.id, track.id, activeTrack, activeModule, track.modules);
                        const isLast = index === track.modules.length - 1;

                        return (
                          <div key={module.id} className="flex items-center">
                            <ModuleNode
                              href={`/modules/${module.id}`}
                              title={module.title}
                              phase={module.phase}
                              skillCount={module.skills.length}
                              state={state}
                              accent={theme.accent}
                              surface={theme.surface}
                            />
                            {isLast ? null : (
                              <div
                                className="h-px min-w-12 border-t border-dashed"
                                style={{ borderColor: state === "todo" ? "var(--shell-border)" : theme.accent }}
                              />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </section>
              );
            })}
          </div>
        </Panel>
      </div>
    </>
  );
}
