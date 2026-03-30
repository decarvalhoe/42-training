import { getDashboardData, getTmuxSessions } from "@/lib/api";

import MentorClient from "./MentorClient";

export const metadata = {
  title: "AI Mentor — 42 Training",
  description: "Pedagogical AI mentor with source policy and terminal context",
};

export default async function MentorPage() {
  const [data, tmux] = await Promise.all([getDashboardData(), getTmuxSessions()]);

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

  const gatewayUrl = process.env.NEXT_PUBLIC_AI_GATEWAY_URL ?? "http://localhost:8100";
  const activeSession = tmux.sessions.find((s) => s.attached)?.name ?? null;

  return (
    <MentorClient
      modules={modules}
      gatewayUrl={gatewayUrl}
      activeSession={activeSession}
      sourceMode={data.sourceMode}
    />
  );
}
