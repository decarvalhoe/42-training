import type { ReactNode } from "react";
import Link from "next/link";

import { getDashboardData } from "@/lib/api";
import type { ModuleItem } from "@/lib/api";

function Pill({ children }: { children: ReactNode }) {
  return <span className="pill">{children}</span>;
}

function deriveModuleState(
  moduleId: string,
  trackId: string,
  activeTrack: string | undefined,
  activeModule: string | undefined,
  modules: ModuleItem[],
): "done" | "in_progress" | "todo" {
  if (trackId !== activeTrack) return "todo";
  if (moduleId === activeModule) return "in_progress";
  const activeIndex = modules.findIndex((m) => m.id === activeModule);
  const currentIndex = modules.findIndex((m) => m.id === moduleId);
  if (activeIndex === -1) return "todo";
  return currentIndex < activeIndex ? "done" : "todo";
}

function prerequisitesMet(
  moduleIndex: number,
  modules: ModuleItem[],
  trackId: string,
  activeTrack: string | undefined,
  activeModule: string | undefined,
): boolean {
  if (moduleIndex === 0) return true;
  for (let i = 0; i < moduleIndex; i++) {
    const state = deriveModuleState(modules[i].id, trackId, activeTrack, activeModule, modules);
    if (state !== "done") return false;
  }
  return true;
}

const stateLabel: Record<string, string> = {
  done: "done",
  in_progress: "in progress",
  todo: "todo",
};

export default async function TrackDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const data = await getDashboardData();
  const { curriculum, progression } = data;

  const track = curriculum.tracks.find((t) => t.id === id);

  if (!track) {
    return (
      <main className="page-shell">
        <section className="section">
          <h1>Track not found</h1>
          <p>No track matches the identifier &ldquo;{id}&rdquo;.</p>
          <Link href="/">Back to dashboard</Link>
        </section>
      </main>
    );
  }

  const activeTrack = progression.learning_plan?.active_course;
  const activeModule = progression.learning_plan?.active_module;

  return (
    <main className="page-shell">
      <section className="section">
        <div>
          <p className="eyebrow">Track</p>
          <h1>{track.title}</h1>
        </div>
        <p className="lead">{track.summary}</p>
        <p>{track.why_it_matters}</p>
      </section>

      <section className="section">
        <div className="section-heading">
          <h2>Modules</h2>
          <span className="muted">{track.modules.length} modules</span>
        </div>
        <div className="module-list">
          {track.modules.map((mod, index) => {
            const state = deriveModuleState(mod.id, track.id, activeTrack, activeModule, track.modules);
            const prereqOk = prerequisitesMet(index, track.modules, track.id, activeTrack, activeModule);
            return (
              <div key={mod.id} className="module-item">
                <div className="module-header">
                  <strong>
                    <Link href={`/modules/${mod.id}`}>{mod.title}</Link>
                  </strong>
                  <div className="stack-list">
                    <Pill>{mod.phase}</Pill>
                    <Pill>{stateLabel[state]}</Pill>
                  </div>
                </div>
                <p>{mod.deliverable}</p>
                <div className="stack-list">
                  {mod.skills.map((skill) => (
                    <Pill key={skill}>{skill}</Pill>
                  ))}
                </div>
                {index > 0 && (
                  <p className="muted prereq-note">
                    Prerequisites: {prereqOk ? "satisfied" : "not yet satisfied"}
                  </p>
                )}
              </div>
            );
          })}
        </div>
      </section>

      <section className="section">
        <Link href="/">Back to dashboard</Link>
      </section>
    </main>
  );
}
