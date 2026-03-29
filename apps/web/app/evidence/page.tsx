import Link from "next/link";

import { getDashboardData } from "@/lib/api";

import EvidenceClient from "./EvidenceClient";

export const metadata = {
  title: "Evidence — 42 Training",
  description: "Browse review and defense evidence artifacts",
};

export default async function EvidencePage() {
  const data = await getDashboardData();
  const modules = data.curriculum.tracks.flatMap((track) =>
    track.modules.map((module) => ({
      id: module.id,
      title: module.title,
      trackId: track.id,
      trackTitle: track.title,
    }))
  );

  return (
    <main className="page-shell evidence-page">
      <nav className="breadcrumb">
        <Link href="/">Dashboard</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Evidence</span>
      </nav>

      <section className="evidence-hero panel">
        <p className="eyebrow">Evidence</p>
        <h1>Keep the artifacts that prove how you reason, not just what you answer.</h1>
        <p className="lead">
          Reviews and oral defenses generate traces: notes, command outputs, summaries and reviewer prompts. This page
          consolidates them in one place so you can revisit weak spots before the next project or evaluation.
        </p>
      </section>

      <EvidenceClient modules={modules} />
    </main>
  );
}
