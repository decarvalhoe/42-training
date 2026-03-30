import { DataSourceBadge } from "@/app/components/DataSourceBadge";
import { GuidedBadge, GuidedPanel, GuidedSidebarSection } from "@/app/components/GuidedSurface";
import { getAnalyticsData } from "@/lib/api";
import type { AnalyticsChartRow } from "@/lib/api";

const TRACK_CLASS: Record<string, string> = {
  shell: "var(--shell-success)",
  c: "var(--shell-warning)",
  python_ai: "var(--shell-info)",
};

function formatMinutes(value: number): string {
  if (value >= 60) {
    return `${(value / 60).toFixed(1)} h`;
  }
  return `${value.toFixed(1)} min`;
}

function metricValue(label: string, value: number): string {
  if (label === "Average time") {
    return formatMinutes(value);
  }
  if (label === "Checkpoint pass rate") {
    return `${value.toFixed(1)}%`;
  }
  return value.toString();
}

function AnalyticsBarChart({
  title,
  eyebrow,
  description,
  rows,
  formatter,
}: {
  title: string;
  eyebrow: string;
  description: string;
  rows: AnalyticsChartRow[];
  formatter: (row: AnalyticsChartRow) => string;
}) {
  const maxValue = rows.length > 0 ? Math.max(...rows.map((row) => row.value), 1) : 1;

  return (
    <GuidedPanel className="px-5 py-5">
      <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">{eyebrow}</p>
      <h2 className="mt-3 font-mono text-lg font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
        {title}
      </h2>
      <p className="mt-3 text-sm leading-7 text-[var(--shell-muted)]">{description}</p>

      {rows.length === 0 ? (
        <p className="mt-5 text-sm leading-6 text-[var(--shell-muted)]">No pedagogical events recorded yet.</p>
      ) : (
        <div className="mt-6 space-y-4">
          {rows.map((row) => {
            const width = `${Math.max((row.value / maxValue) * 100, 6)}%`;

            return (
              <div key={row.module_id} className="space-y-2">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <strong className="font-mono text-sm uppercase tracking-[0.08em] text-[var(--shell-ink)]">
                      {row.module_title}
                    </strong>
                    <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-dim)]">
                      {row.track_id} · {row.phase}
                    </p>
                  </div>
                  <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-ink)]">
                    {formatter(row)}
                  </span>
                </div>
                <div className="h-2 overflow-hidden border border-[var(--shell-border)] bg-[var(--shell-sidebar)]">
                  <div className="h-full" style={{ width, backgroundColor: TRACK_CLASS[row.track_id] ?? "var(--shell-success)" }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </GuidedPanel>
  );
}

export default async function AnalyticsPage() {
  const analytics = await getAnalyticsData();

  const summaryCards = [
    { label: "Pedagogical events", value: analytics.summary.total_events },
    { label: "Modules completed", value: analytics.summary.module_completions },
    { label: "Average time", value: analytics.summary.average_completion_minutes },
    { label: "Checkpoint pass rate", value: analytics.summary.checkpoint_success_rate },
    { label: "Mentor queries", value: analytics.summary.mentor_queries },
    { label: "Defenses started", value: analytics.summary.defenses_started },
    { label: "Watch check-ins", value: analytics.summary.watch_mentor_checkins },
  ];

  return (
    <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
      <div className="grid gap-4">
        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Analytics">
            <h1 className="font-mono text-2xl font-semibold uppercase tracking-[0.08em] text-[var(--shell-ink)]">
              Pedagogical event stream
            </h1>
            <p className="text-sm leading-7 text-[var(--shell-muted)]">
              Internal product view of learner throughput, checkpoint reliability and guided workflow intensity.
            </p>
            <div className="pt-2">
              <DataSourceBadge sourceMode={analytics.sourceMode} />
            </div>
          </GuidedSidebarSection>
        </GuidedPanel>

        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Summary">
            <div className="grid gap-3">
              {summaryCards.slice(0, 4).map((card) => (
                <div key={card.label} className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
                  <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">{card.label}</p>
                  <p className="mt-3 font-mono text-xl font-semibold text-[var(--shell-ink)]">
                    {metricValue(card.label, card.value)}
                  </p>
                </div>
              ))}
            </div>
          </GuidedSidebarSection>
        </GuidedPanel>

        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Workflow intensity">
            <div className="flex flex-wrap gap-2">
              <GuidedBadge>mentor {analytics.summary.mentor_queries}</GuidedBadge>
              <GuidedBadge>defense {analytics.summary.defenses_started}</GuidedBadge>
              <GuidedBadge>watch {analytics.summary.watch_mentor_checkins}</GuidedBadge>
            </div>
          </GuidedSidebarSection>
        </GuidedPanel>
      </div>

      <div className="grid gap-4">
        <GuidedPanel className="px-6 py-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
            analytics // pedagogical events
          </p>
          <h2 className="mt-4 font-mono text-2xl font-semibold uppercase tracking-[0.08em] text-[var(--shell-ink)]">
            Analytics dashboard
          </h2>
          <p className="mt-4 max-w-3xl text-sm leading-7 text-[var(--shell-muted)]">
            Product and pedagogy stay connected here: event volume, completion pace and checkpoint quality all read as one coherent workflow family.
          </p>
        </GuidedPanel>

        <div className="grid gap-4 xl:grid-cols-2">
          <AnalyticsBarChart
            eyebrow="Product throughput"
            title="Modules completed"
            description="Completion counts derived from pedagogical event logs."
            rows={analytics.modules_completed}
            formatter={(row) => `${row.count}${row.suffix}`}
          />
          <AnalyticsBarChart
            eyebrow="Learning pace"
            title="Average time to complete"
            description="Average minutes between module_started and module_completed for the same learner/module pair."
            rows={analytics.average_time}
            formatter={(row) => formatMinutes(row.value)}
          />
        </div>

        <AnalyticsBarChart
          eyebrow="Pedagogical quality"
          title="Checkpoint pass rate"
          description="Pass rate based on checkpoint_submitted events and self-evaluation payloads."
          rows={analytics.success_rate}
          formatter={(row) => `${row.value.toFixed(1)}% · ${row.count} submissions`}
        />
      </div>
    </div>
  );
}
