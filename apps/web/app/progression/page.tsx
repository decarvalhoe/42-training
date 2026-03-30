import Link from "next/link";
import type { ReactNode } from "react";

import { getDashboardData } from "@/lib/api";
import { getLearningContext, getTrackTheme } from "@/lib/learner-progress";

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

function ActionLink({
  href,
  label,
  variant = "primary",
}: {
  href: string;
  label: string;
  variant?: "primary" | "secondary";
}) {
  const className =
    variant === "primary"
      ? "border-[var(--shell-success)] bg-[var(--shell-success)] text-[var(--shell-canvas)] hover:bg-[var(--shell-success-strong)]"
      : "border-[var(--shell-border-strong)] text-[var(--shell-ink)] hover:border-[var(--shell-success)] hover:text-[var(--shell-success)]";

  return (
    <Link
      href={href}
      className={`inline-flex min-h-11 items-center justify-center border px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.28em] transition-colors ${className}`}
    >
      {label}
    </Link>
  );
}

function ModuleListItem({
  href,
  eyebrow,
  title,
  detail,
  badge,
  accent,
}: {
  href: string;
  eyebrow: string;
  title: string;
  detail: string;
  badge: string;
  accent: string;
}) {
  return (
    <Link
      href={href}
      className="block border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4 transition-colors hover:border-[var(--shell-success)]"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.28em]" style={{ color: accent }}>
            {eyebrow}
          </p>
          <h3 className="mt-2 font-mono text-sm font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
            {title}
          </h3>
        </div>
        <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">{badge}</span>
      </div>
      <p className="mt-3 text-sm leading-6 text-[var(--shell-muted)]">{detail}</p>
    </Link>
  );
}

export default async function ProgressionPage() {
  const data = await getDashboardData();
  const { progression } = data;
  const { activeTrack, learnerMode, modules, nextReadyModule, trackStats } = getLearningContext(data);
  const activeModules = modules.filter((entry) => entry.state === "in_progress");
  const completedModules = modules.filter((entry) => entry.state === "done");

  const stateById = new Map(modules.map((entry) => [entry.module.id, entry.state]));
  const readyModules = modules.filter((entry) => {
    if (entry.state !== "todo") {
      return false;
    }

    const prerequisites = entry.module.prerequisites ?? [];
    return prerequisites.every((prerequisiteId) => stateById.get(prerequisiteId) === "done");
  });
  const lockedModules = modules.filter((entry) => entry.state === "todo" && !readyModules.some((ready) => ready.module.id === entry.module.id));

  const totalModules = modules.length;
  const percentComplete = totalModules === 0 ? 0 : Math.round((completedModules.length / totalModules) * 100);
  const activeTrackStats = trackStats.find((track) => track.id === activeTrack) ?? trackStats[0] ?? null;

  const headline =
    learnerMode === "active"
      ? "Keep the next move obvious"
      : learnerMode === "returning"
        ? "Restart from the next ready module"
        : "Shape the first runway";

  const lead =
    learnerMode === "active"
      ? "Progression is now the planning surface. It shows what is currently active, what can be started immediately and what remains blocked by prerequisites."
      : learnerMode === "returning"
        ? "The learner journey no longer lives in the home page. This surface is where you decide how to re-enter, review readiness and sequence the next modules."
        : "Before any real momentum exists, progression should show the unlocked entry points clearly and keep the rest of the curriculum in the background.";

  const primaryAction =
    activeModules[0] !== undefined
      ? { href: `/modules/${activeModules[0].module.id}`, label: "Resume active module" }
      : nextReadyModule !== null
        ? { href: `/modules/${nextReadyModule.module.id}`, label: "Start next module" }
        : { href: "/tracks", label: "Inspect tracks" };

  return (
    <div className="grid gap-6">
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_320px]">
        <Panel className="px-6 py-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
            progression // next-step planning
          </p>
          <h1 className="mt-4 font-mono text-3xl font-semibold uppercase tracking-[0.08em] text-[var(--shell-ink)] md:text-4xl">
            {headline}
          </h1>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-[var(--shell-muted)]">{lead}</p>

          <div className="mt-8 flex flex-wrap gap-3">
            <ActionLink href={primaryAction.href} label={primaryAction.label} />
            <ActionLink href="/dashboard" label="Open skill graph" variant="secondary" />
            <ActionLink href="/tracks" label="Inspect tracks" variant="secondary" />
          </div>

          <div className="mt-8 grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
            <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
              <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Overall completion</p>
              <p className="mt-3 font-mono text-lg font-semibold text-[var(--shell-ink)]">{percentComplete}%</p>
              <p className="mt-2 font-mono text-[10px] leading-5 text-[var(--shell-muted)]">
                {completedModules.length}/{totalModules} modules cleared
              </p>
            </div>
            <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
              <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Ready now</p>
              <p className="mt-3 font-mono text-lg font-semibold text-[var(--shell-ink)]">{readyModules.length}</p>
              <p className="mt-2 font-mono text-[10px] leading-5 text-[var(--shell-muted)]">
                Modules that can start immediately without missing prerequisites
              </p>
            </div>
            <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
              <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Blocked</p>
              <p className="mt-3 font-mono text-lg font-semibold text-[var(--shell-ink)]">{lockedModules.length}</p>
              <p className="mt-2 font-mono text-[10px] leading-5 text-[var(--shell-muted)]">
                Modules still waiting on earlier checkpoints
              </p>
            </div>
            <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
              <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Current track</p>
              <p className="mt-3 font-mono text-lg font-semibold text-[var(--shell-ink)]">
                {getTrackTheme(activeTrack).label}
              </p>
              <p className="mt-2 font-mono text-[10px] leading-5 text-[var(--shell-muted)]">
                {activeTrackStats?.percentComplete ?? 0}% complete · {progression.progress?.current_step ?? "No active step"}
              </p>
            </div>
          </div>
        </Panel>

        <Panel className="px-5 py-5">
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Next recommended</p>
          <div className="mt-4 border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
            <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">
              {nextReadyModule?.trackTitle ?? "No unlocked module"}
            </p>
            <h2 className="mt-3 font-mono text-base font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
              {nextReadyModule?.module.title ?? "Awaiting prerequisites"}
            </h2>
            <p className="mt-3 text-sm leading-6 text-[var(--shell-muted)]">
              {nextReadyModule?.module.deliverable ?? "Complete the currently blocked prerequisites to reveal the next recommended module."}
            </p>
            {nextReadyModule !== null ? (
              <div className="mt-5">
                <ActionLink href={`/modules/${nextReadyModule.module.id}`} label="Open module" />
              </div>
            ) : null}
          </div>
        </Panel>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <Panel className="px-5 py-5">
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Active</p>
          <h2 className="mt-3 font-mono text-lg font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
            In progress
          </h2>
          <div className="mt-5 space-y-3">
            {activeModules.length === 0 ? (
              <p className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4 text-sm leading-6 text-[var(--shell-muted)]">
                No module is currently active. Use the ready column to pick the next checkpoint.
              </p>
            ) : (
              activeModules.map((entry) => (
                <ModuleListItem
                  key={entry.module.id}
                  href={`/modules/${entry.module.id}`}
                  eyebrow={entry.trackTitle}
                  title={entry.module.title}
                  detail={entry.module.deliverable}
                  badge="active"
                  accent="var(--shell-warning)"
                />
              ))
            )}
          </div>
        </Panel>

        <Panel className="px-5 py-5">
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Ready</p>
          <h2 className="mt-3 font-mono text-lg font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
            Startable now
          </h2>
          <div className="mt-5 space-y-3">
            {readyModules.length === 0 ? (
              <p className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4 text-sm leading-6 text-[var(--shell-muted)]">
                Nothing is ready yet. Clear the active module or missing prerequisites to unlock the next lane.
              </p>
            ) : (
              readyModules.map((entry) => (
                <ModuleListItem
                  key={entry.module.id}
                  href={`/modules/${entry.module.id}`}
                  eyebrow={entry.trackTitle}
                  title={entry.module.title}
                  detail={entry.module.deliverable}
                  badge={entry.module.phase}
                  accent={getTrackTheme(entry.trackId).accent}
                />
              ))
            )}
          </div>
        </Panel>

        <Panel className="px-5 py-5">
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Completed</p>
          <h2 className="mt-3 font-mono text-lg font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
            Cleared checkpoints
          </h2>
          <div className="mt-5 space-y-3">
            {completedModules.length === 0 ? (
              <p className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4 text-sm leading-6 text-[var(--shell-muted)]">
                Nothing has been completed yet. The first completed module will show up here.
              </p>
            ) : (
              completedModules.map((entry) => (
                <ModuleListItem
                  key={entry.module.id}
                  href={`/modules/${entry.module.id}`}
                  eyebrow={entry.trackTitle}
                  title={entry.module.title}
                  detail={entry.module.deliverable}
                  badge="done"
                  accent={getTrackTheme(entry.trackId).accent}
                />
              ))
            )}
          </div>
        </Panel>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Panel className="px-6 py-6">
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Track pacing</p>
          <div className="mt-5 grid gap-4 lg:grid-cols-3">
            {trackStats.map((track) => {
              const theme = getTrackTheme(track.id);
              const focusModule = track.activeModule ?? track.nextReadyModule;

              return (
                <Link
                  key={track.id}
                  href={`/tracks/${track.id}`}
                  className="border px-4 py-4 transition-colors hover:border-[var(--shell-success)]"
                  style={{ borderColor: theme.border, backgroundColor: theme.surface }}
                >
                  <p className="font-mono text-[9px] uppercase tracking-[0.28em]" style={{ color: theme.accent }}>
                    {theme.label}
                  </p>
                  <h3 className="mt-3 font-mono text-base font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                    {track.title}
                  </h3>
                  <div className="mt-4 h-2 overflow-hidden border border-[var(--shell-border)] bg-[var(--shell-canvas)]">
                    <div
                      className="h-full"
                      style={{ width: `${track.percentComplete}%`, backgroundColor: theme.accent }}
                    />
                  </div>
                  <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
                    {track.completedModules}/{track.totalModules} modules
                  </p>
                  <p className="mt-3 text-sm text-[var(--shell-ink)]">
                    {focusModule?.title ?? "No module unlocked yet"}
                  </p>
                </Link>
              );
            })}
          </div>
        </Panel>

        <Panel className="px-6 py-6">
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Still locked</p>
          <h2 className="mt-3 font-mono text-xl font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
            Hidden behind prerequisites
          </h2>
          <div className="mt-5 space-y-3">
            {lockedModules.length === 0 ? (
              <p className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4 text-sm leading-6 text-[var(--shell-muted)]">
                Nothing is blocked right now. The learner can move directly into the ready lane.
              </p>
            ) : (
              lockedModules.map((entry) => (
                <div
                  key={entry.module.id}
                  className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4"
                >
                  <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">
                    {entry.trackTitle}
                  </p>
                  <h3 className="mt-2 font-mono text-sm font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                    {entry.module.title}
                  </h3>
                  <p className="mt-3 text-sm leading-6 text-[var(--shell-muted)]">
                    {(entry.module.prerequisites ?? []).length === 0
                      ? "No prerequisites listed, but the module is still waiting on graph sequencing."
                      : `Requires: ${(entry.module.prerequisites ?? []).join(", ")}`}
                  </p>
                </div>
              ))
            )}
          </div>
        </Panel>
      </section>
    </div>
  );
}
