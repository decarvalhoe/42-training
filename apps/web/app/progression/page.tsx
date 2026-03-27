import type { ReactNode } from "react";

import { getDashboardData } from "@/lib/api";

function Pill({ children }: { children: ReactNode }) {
  return <span className="pill">{children}</span>;
}

export default async function ProgressionPage() {
  const data = await getDashboardData();
  const { progression } = data;
  const plan = progression.learning_plan;
  const progress = progression.progress;

  return (
    <main className="page-shell">
      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Progression</p>
          <h1>Your learning progress</h1>
        </div>

        <div className="hero-grid">
          <div className="metric-card">
            <span>Active course</span>
            <strong>{plan?.active_course ?? "n/a"}</strong>
          </div>
          <div className="metric-card">
            <span>Active module</span>
            <strong>{plan?.active_module ?? "n/a"}</strong>
          </div>
          <div className="metric-card">
            <span>Pace mode</span>
            <strong>{plan?.pace_mode ?? "self_paced"}</strong>
          </div>
          <div className="metric-card">
            <span>Next command</span>
            <strong>{progression.next_command ?? "n/a"}</strong>
          </div>
        </div>
      </section>

      {progress && (
        <section className="section">
          <h2>Current exercise</h2>
          <p><strong>{progress.current_exercise ?? "None"}</strong></p>
          <p className="muted">{progress.current_step ?? "No current step"}</p>

          <h3>Completed</h3>
          <div className="stack-list">
            {(progress.completed ?? []).map((item) => (
              <Pill key={item}>{item}</Pill>
            ))}
          </div>

          <h3>In progress</h3>
          <div className="stack-list">
            {(progress.in_progress ?? []).map((item) => (
              <Pill key={item}>{item}</Pill>
            ))}
          </div>

          <h3>To do</h3>
          <div className="stack-list">
            {(progress.todo ?? []).map((item) => (
              <Pill key={item}>{item}</Pill>
            ))}
          </div>
        </section>
      )}
    </main>
  );
}
