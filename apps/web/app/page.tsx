import type { ReactNode } from "react";

import { getDashboardData } from "@/lib/api";
import { SourcePolicyBadge } from "@/app/components/SourcePolicyBadge";

function Pill({ children }: { children: ReactNode }) {
  return <span className="pill">{children}</span>;
}

export default async function HomePage() {
  const data = await getDashboardData();
  const { curriculum, progression } = data;
  const activeCourse = progression.learning_plan?.active_course ?? "shell";

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">42-training / MVP</p>
          <h1>One learning system, three tracks, one disciplined AI policy.</h1>
          <p className="lead">
            This app prepares a self-paced learner for 42 Lausanne through Shell, C and Python + AI,
            while keeping the 42 philosophy intact: autonomy, projects, peer-style reasoning and no blind copying.
          </p>
          <div className="hero-grid">
            <div className="metric-card">
              <span>Campus</span>
              <strong>{curriculum.metadata.campus}</strong>
            </div>
            <div className="metric-card">
              <span>Active course</span>
              <strong>{activeCourse}</strong>
            </div>
            <div className="metric-card">
              <span>Pace mode</span>
              <strong>{progression.learning_plan?.pace_mode ?? "self_paced"}</strong>
            </div>
            <div className="metric-card">
              <span>Next command</span>
              <strong>{progression.next_command ?? "n/a"}</strong>
            </div>
          </div>
        </div>
        <aside className="status-panel">
          <h2>Current session</h2>
          <p>{progression.progress?.current_exercise ?? "No active exercise"}</p>
          <p>{progression.progress?.current_step ?? "No current step"}</p>
          <div className="stack-list">
            {(progression.progress?.in_progress ?? []).map((item) => (
              <Pill key={item}>{item}</Pill>
            ))}
          </div>
        </aside>
      </section>

      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Tracks</p>
          <h2>Triple-track architecture</h2>
        </div>
        <div className="track-grid">
          {curriculum.tracks.map((track) => (
            <article key={track.id} className={`track-card ${track.id === activeCourse ? "active" : ""}`}>
              <div className="card-topline">
                <span>{track.id}</span>
                <span>{track.modules.length} modules</span>
              </div>
              <h3>{track.title}</h3>
              <p>{track.summary}</p>
              <p className="muted">{track.why_it_matters}</p>
              <div className="module-list">
                {track.modules.map((module) => (
                  <div key={module.id} className="module-item">
                    <div className="module-header">
                      <strong>{module.title}</strong>
                      <Pill>{module.phase}</Pill>
                    </div>
                    <p>{module.deliverable}</p>
                    <div className="stack-list">
                      {module.skills.map((skill) => (
                        <Pill key={skill}>{skill}</Pill>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="section split">
        <article className="panel">
          <p className="eyebrow">Bridges</p>
          <h2>Preparation checkpoints</h2>
          <div className="bridge-list">
            {curriculum.bridges.map((bridge) => (
              <div key={bridge.id} className="bridge-item">
                <strong>{bridge.title}</strong>
                <div className="stack-list">
                  {bridge.recommended_modules.map((item) => (
                    <Pill key={item}>{item}</Pill>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </article>
        <article className="panel">
          <p className="eyebrow">RAG Guardrails</p>
          <h2>Source policy</h2>
          <div className="policy-list">
            {curriculum.source_policy.tiers.map((tier) => (
              <div key={tier.id} className="policy-item">
                <strong>{tier.label}</strong>
                <SourcePolicyBadge tier={tier.id} />
              </div>
            ))}
          </div>
        </article>
      </section>
    </main>
  );
}
