import type { ReactNode } from "react";

import { getDashboardData } from "@/lib/api";

function Pill({ children }: { children: ReactNode }) {
  return <span className="pill">{children}</span>;
}

export default async function ModulePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const data = await getDashboardData();

  let foundModule = null;
  let parentTrack = null;

  for (const track of data.curriculum.tracks) {
    const mod = track.modules.find((m) => m.id === id);
    if (mod) {
      foundModule = mod;
      parentTrack = track;
      break;
    }
  }

  if (!foundModule || !parentTrack) {
    return (
      <main className="page-shell">
        <h1>Module not found</h1>
        <p>No module matching &ldquo;{id}&rdquo;.</p>
      </main>
    );
  }

  return (
    <main className="page-shell">
      <section className="section">
        <div className="section-heading">
          <p className="eyebrow">Module &middot; {parentTrack.title}</p>
          <h1>{foundModule.title}</h1>
        </div>
        <Pill>{foundModule.phase}</Pill>
        <p className="lead">{foundModule.deliverable}</p>
        <div className="stack-list">
          {foundModule.skills.map((skill) => (
            <Pill key={skill}>{skill}</Pill>
          ))}
        </div>
      </section>
    </main>
  );
}
