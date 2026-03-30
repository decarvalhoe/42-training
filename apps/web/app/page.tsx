import Link from "next/link";
import type { ReactNode } from "react";

import { DataSourceBadge } from "@/app/components/DataSourceBadge";
import { getAnalyticsData, getDashboardData, getTmuxSessions } from "@/lib/api";
import { countSkills, getLearningContext, getTrackTheme, summarizeSessions } from "@/lib/learner-progress";

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

function MetricTile({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
      <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">{label}</p>
      <p className="mt-3 font-mono text-lg font-semibold text-[var(--shell-ink)]">{value}</p>
      <p className="mt-2 font-mono text-[10px] leading-5 text-[var(--shell-muted)]">{detail}</p>
    </div>
  );
}

function FocusCard({
  href,
  eyebrow,
  title,
  body,
}: {
  href: string;
  eyebrow: string;
  title: string;
  body: string;
}) {
  return (
    <Link
      href={href}
      className="group flex h-full flex-col justify-between border border-[var(--shell-border)] bg-[var(--shell-panel)] px-5 py-5 transition-colors hover:border-[var(--shell-success)]"
    >
      <div>
        <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">{eyebrow}</p>
        <h2 className="mt-3 font-mono text-base font-semibold uppercase tracking-[0.14em] text-[var(--shell-ink)]">
          {title}
        </h2>
        <p className="mt-3 text-sm leading-6 text-[var(--shell-muted)]">{body}</p>
      </div>
      <span className="mt-6 font-mono text-[10px] uppercase tracking-[0.28em] text-[var(--shell-success)]">
        Open
      </span>
    </Link>
  );
}

export default async function HomePage() {
  const [data, analytics, tmuxData] = await Promise.all([
    getDashboardData(),
    getAnalyticsData(),
    getTmuxSessions(),
  ]);

  const { curriculum, progression } = data;
  const { activeTrack, activeModule, learnerMode, modules, nextReadyModule, trackStats } = getLearningContext(data);
  const activeEntry = modules.find((entry) => entry.module.id === activeModule) ?? null;
  const activeTrackStats = trackStats.find((track) => track.id === activeTrack) ?? trackStats[0] ?? null;
  const readyNow = modules.filter((entry) => entry.state === "todo").slice(0, 3);
  const totalModules = modules.length;
  const completedModules = modules.filter((entry) => entry.state === "done").length;
  const inProgressModules = modules.filter((entry) => entry.state === "in_progress").length;
  const tmuxSummary = summarizeSessions(tmuxData.sessions);
  const totalSkills = countSkills(curriculum.tracks);

  const headline =
    learnerMode === "active"
      ? `Resume ${activeEntry?.module.title ?? "your current module"}`
      : learnerMode === "returning"
        ? "Pick the next unlocked checkpoint"
        : "Start your first learning lane";

  const lead =
    learnerMode === "active"
      ? "Home is now the session-entry surface: current module, next command and workspace health are visible before you dive back into the graph."
      : learnerMode === "returning"
        ? "You already have momentum. Re-enter from the next ready module, then branch into the graph or the progression plan when you need more context."
        : "The first run should be simple: understand the learning contract, choose a track and launch the first module without reading the entire curriculum first.";

  const primaryAction =
    activeEntry !== null
      ? { href: `/modules/${activeEntry.module.id}`, label: "Resume module" }
      : nextReadyModule !== null
        ? { href: `/modules/${nextReadyModule.module.id}`, label: "Open next module" }
        : { href: "/tracks", label: "Explore tracks" };

  const immediateDecisions =
    nextReadyModule === null
      ? readyNow
      : [nextReadyModule, ...readyNow.filter((entry) => entry.module.id !== nextReadyModule.module.id)];

  return (
    <div className="grid gap-6">
      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.4fr)_320px]">
        <Panel className="px-6 py-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="max-w-3xl">
              <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
                mission control // learner home
              </p>
              <h1 className="mt-4 font-mono text-3xl font-semibold uppercase tracking-[0.08em] text-[var(--shell-ink)] md:text-4xl">
                {headline}
              </h1>
              <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--shell-muted)]">{lead}</p>
            </div>
            <DataSourceBadge sourceMode={data.sourceMode} />
          </div>

          <div className="mt-8 flex flex-wrap gap-3">
            <ActionLink href={primaryAction.href} label={primaryAction.label} />
            <ActionLink href="/dashboard" label="Open skill graph" variant="secondary" />
            <ActionLink href="/progression" label="Review progression" variant="secondary" />
          </div>

          <div className="mt-8 grid gap-3 md:grid-cols-2 2xl:grid-cols-4">
            <MetricTile
              label="Active track"
              value={getTrackTheme(activeTrack).label}
              detail={activeTrackStats?.summary ?? "The current learning lane selected for this learner profile."}
            />
            <MetricTile
              label="Current exercise"
              value={progression.progress?.current_exercise ?? "Awaiting launch"}
              detail={progression.progress?.current_step ?? "No active step yet."}
            />
            <MetricTile
              label="Next command"
              value={progression.next_command ?? "No command queued"}
              detail={activeEntry?.module.deliverable ?? "The next concrete learner action is not defined yet."}
            />
            <MetricTile
              label="Coverage"
              value={`${completedModules}/${totalModules}`}
              detail={`${inProgressModules} active module · ${totalSkills} skills across ${curriculum.tracks.length} tracks`}
            />
          </div>
        </Panel>

        <div className="grid gap-4">
          <Panel className="px-5 py-5">
            <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Session pulse</p>
            <h2 className="mt-3 font-mono text-base font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
              Workspace health
            </h2>
            <div className="mt-5 grid gap-3">
              <div className="flex items-center justify-between border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-3 font-mono text-[10px] uppercase tracking-[0.24em]">
                <span className="text-[var(--shell-muted)]">Sessions live</span>
                <span className="text-[var(--shell-success)]">{tmuxSummary.active}</span>
              </div>
              <div className="flex items-center justify-between border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-3 font-mono text-[10px] uppercase tracking-[0.24em]">
                <span className="text-[var(--shell-muted)]">Idle panes</span>
                <span className="text-[var(--shell-ink)]">{tmuxSummary.idle}</span>
              </div>
              <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
                <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Primary tmux</p>
                <p className="mt-3 font-mono text-sm text-[var(--shell-ink)]">
                  {tmuxSummary.primary?.name ?? "No session attached"}
                </p>
                <p className="mt-2 font-mono text-[10px] leading-5 text-[var(--shell-muted)]">
                  {tmuxSummary.primary === null
                    ? "The learner workspace is currently offline."
                    : `${tmuxSummary.primary.status} · ${tmuxSummary.primary.windows} windows · last activity ${tmuxSummary.primary.last_activity}`}
                </p>
              </div>
            </div>
          </Panel>

          <Panel className="px-5 py-5">
            <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Learning contract</p>
            <div className="mt-4 space-y-3 text-sm leading-6 text-[var(--shell-muted)]">
              <p>Official references remain the ground truth. Community material is explanation-only and direct solution content stays blocked.</p>
              <p>Mentor interactions are meant to question and guide, not shortcut the learner’s reasoning.</p>
              <p>Evidence, review and defense happen after the module checkpoint, not before the learner engages with the work.</p>
            </div>
          </Panel>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-3">
        <FocusCard
          href="/dashboard"
          eyebrow="Dashboard"
          title="See the skill graph"
          body="Use the graph surface when you need the global competency map, state legend and cross-track visibility."
        />
        <FocusCard
          href="/tracks"
          eyebrow="Tracks"
          title="Explore the curriculum"
          body="Open the track explorer to inspect dependencies, prerequisites and where a module sits inside its learning lane."
        />
        <FocusCard
          href="/progression"
          eyebrow="Progression"
          title="Plan the next steps"
          body="Use progression to decide what is ready now, what stays blocked and what has already been completed."
        />
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <Panel className="px-6 py-6">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Track lanes</p>
              <h2 className="mt-3 font-mono text-xl font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                Progress by learning lane
              </h2>
            </div>
            <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-[var(--shell-muted)]">
              {analytics.summary.module_completions} completions recorded
            </p>
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-3">
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
                  <p className="mt-3 text-sm leading-6 text-[var(--shell-muted)]">{track.summary}</p>
                  <div className="mt-4 h-2 overflow-hidden border border-[var(--shell-border)] bg-[var(--shell-canvas)]">
                    <div
                      className="h-full"
                      style={{ width: `${track.percentComplete}%`, backgroundColor: theme.accent }}
                    />
                  </div>
                  <p className="mt-3 font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
                    {track.completedModules}/{track.totalModules} modules · {track.totalSkills} skills
                  </p>
                  <p className="mt-2 text-sm text-[var(--shell-ink)]">
                    {focusModule?.title ?? "No module unlocked yet"}
                  </p>
                </Link>
              );
            })}
          </div>
        </Panel>

        <Panel className="px-6 py-6">
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Ready now</p>
          <h2 className="mt-3 font-mono text-xl font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
            Immediate learner decisions
          </h2>
          <div className="mt-6 space-y-3">
            {immediateDecisions.slice(0, 4).map((entry) => {
              const theme = getTrackTheme(entry.trackId);
              return (
                <Link
                  key={entry.module.id}
                  href={`/modules/${entry.module.id}`}
                  className="block border px-4 py-4 transition-colors hover:border-[var(--shell-success)]"
                  style={{ borderColor: theme.border, backgroundColor: "var(--shell-canvas)" }}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-mono text-[9px] uppercase tracking-[0.28em]" style={{ color: theme.accent }}>
                        {theme.label}
                      </p>
                      <h3 className="mt-2 font-mono text-sm font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                        {entry.module.title}
                      </h3>
                    </div>
                    <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
                      {entry.module.phase}
                    </span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-[var(--shell-muted)]">{entry.module.deliverable}</p>
                </Link>
              );
            })}
          </div>
        </Panel>
      </section>
    </div>
  );
}
