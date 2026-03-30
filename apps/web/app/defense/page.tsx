import { getDashboardData, getTmuxSessions } from "@/lib/api";

import DefenseClient from "./DefenseClient";

export const metadata = {
  title: "Defense — 42 Training",
  description: "Oral defense and guided review for 42 Lausanne preparation",
};

export default async function DefensePage() {
  const data = await getDashboardData();

  /* Flatten all modules with their track context */
  const modules = data.curriculum.tracks.flatMap((track) =>
    track.modules.map((mod) => ({
      id: mod.id,
      title: mod.title,
      phase: mod.phase,
      trackId: track.id,
      trackTitle: track.title,
      skillCount: mod.skills.length,
      deliverable: mod.deliverable,
    }))
  );

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  /* Fetch available tmux sessions so the learner can attach terminal context */
  const tmuxData = await getTmuxSessions();
  const tmuxSessions = tmuxData.sessions.map((s) => ({
    name: s.name,
    status: s.status,
    attached: s.attached,
  }));

  return (
    <DefenseClient
      modules={modules}
      apiUrl={apiUrl}
      tmuxSessions={tmuxSessions}
      sourceMode={data.sourceMode}
    />
  );
}
