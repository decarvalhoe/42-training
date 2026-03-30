import Link from "next/link";

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
    }))
  );

  const gatewayUrl = process.env.NEXT_PUBLIC_AI_GATEWAY_URL ?? "http://localhost:8100";
  const activeSession = tmux.sessions.find((s) => s.attached)?.name ?? null;

  return (
    <main className="page-shell mentor-page">
      <nav className="breadcrumb">
        <Link href="/">Dashboard</Link>
        <span className="breadcrumb-sep">/</span>
        <span>AI Mentor</span>
      </nav>

      <section className="panel mentor-hero">
        <p className="eyebrow">AI Mentor</p>
        <h1>Guided learning, not shortcuts</h1>
        <p className="lead">
          Ask questions about your current module. The mentor responds with
          observations, questions and hints following the 42 philosophy. Source
          provenance and confidence levels are shown for every response.
        </p>
      </section>

      <MentorClient
        modules={modules}
        gatewayUrl={gatewayUrl}
        activeSession={activeSession}
      />
    </main>
  );
}
