import type { ReactNode } from "react";

import { getDashboardData } from "@/lib/api";

function Pill({ children }: { children: ReactNode }) {
  return <span className="pill">{children}</span>;
}

export default async function TrackPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await getDashboardData();
  const track = data.curriculum.tracks.find((t) => t.id === id);

  if (!track) {
    return (
      <main className="page-shell">
        <h1>Track not found</h1>
        <p>No track matching &ldquo;{id}&rdquo;.</p>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Track</p>
          <h1>{track.title}</h1>
        </div>
        <p className="lead">{track.summary}</p>
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
      </section>
    </main>
  );
}
