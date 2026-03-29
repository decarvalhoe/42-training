import Link from "next/link";

import { getDashboardData } from "@/lib/api";

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
    }))
  );

  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  return (
    <main className="page-shell defense-page">
      <nav className="breadcrumb">
        <Link href="/">Dashboard</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Defense</span>
      </nav>

      <section className="defense-hero panel">
        <p className="eyebrow">Oral defense</p>
        <h1>Defense and guided review</h1>
        <p className="lead">
          Test your understanding of module skills through timed questions.
          Explain concepts in your own words — no solutions are provided. This
          simulates the 42-style oral defense where you must demonstrate genuine
          understanding.
        </p>
      </section>

      <DefenseClient modules={modules} apiUrl={apiUrl} />
    </main>
  );
}
