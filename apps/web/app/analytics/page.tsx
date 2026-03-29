import Link from "next/link";

import { getAnalyticsData } from "@/lib/api";
import type { AnalyticsChartRow } from "@/lib/api";

const TRACK_CLASS: Record<string, string> = {
  shell: "track-shell",
  c: "track-c",
  python_ai: "track-python",
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
    <article className="panel analytics-chart-panel">
      <p className="eyebrow">{eyebrow}</p>
      <h2>{title}</h2>
      <p className="muted analytics-chart-copy">{description}</p>

      {rows.length === 0 ? (
        <p className="muted">No pedagogical events recorded yet.</p>
      ) : (
        <div className="analytics-bar-list">
          {rows.map((row) => {
            const width = `${Math.max((row.value / maxValue) * 100, 6)}%`;
            return (
              <div key={row.module_id} className="analytics-bar-row">
                <div className="analytics-bar-header">
                  <div>
                    <strong>{row.module_title}</strong>
                    <p className="muted">
                      {row.track_id} &middot; {row.phase}
                    </p>
                  </div>
                  <span className="analytics-bar-value">{formatter(row)}</span>
                </div>
                <div className={`analytics-bar-track ${TRACK_CLASS[row.track_id] ?? ""}`}>
                  <div
                    className="analytics-bar-fill"
                    style={{ width }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </article>
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
    <main className="page-shell">
      <nav className="breadcrumb">
        <Link href="/">Dashboard</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Analytics</span>
      </nav>

      <section className="panel analytics-hero">
        <p className="eyebrow">Product and pedagogy</p>
        <h1>Analytics dashboard</h1>
        <p className="lead">
          A first internal view of pedagogical events, module throughput and checkpoint quality,
          aligned with the KPI definitions from <code>docs/PRODUCT_METRICS.md</code>.
        </p>

        <div className="analytics-summary-grid">
          {summaryCards.map((card) => (
            <div key={card.label} className="metric-card">
              <span>{card.label}</span>
              <strong>{metricValue(card.label, card.value)}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="analytics-grid">
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
        <AnalyticsBarChart
          eyebrow="Pedagogical quality"
          title="Checkpoint pass rate"
          description="Pass rate based on checkpoint_submitted events and self-evaluation payloads."
          rows={analytics.success_rate}
          formatter={(row) => `${row.value.toFixed(1)}% · ${row.count} submissions`}
        />
      </section>
    </main>
  );
}
