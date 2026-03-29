import Link from "next/link";

import { getDashboardData } from "@/lib/api";

import ReviewClient from "./ReviewClient";

export const metadata = {
  title: "Guided Review — 42 Training",
  description: "Submit code for guided peer-style review and track attached evidence",
};

export default async function ReviewPage() {
  const data = await getDashboardData();
  const modules = data.curriculum.tracks.flatMap((track) =>
    track.modules.map((module) => ({
      id: module.id,
      title: module.title,
      phase: module.phase,
      trackId: track.id,
      trackTitle: track.title,
    }))
  );

  return (
    <main className="page-shell review-page">
      <nav className="breadcrumb">
        <Link href="/">Dashboard</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Review</span>
      </nav>

      <section className="review-hero panel">
        <p className="eyebrow">Guided review</p>
        <h1>Prepare a peer-style review before the real evaluation pressure hits.</h1>
        <p className="lead">
          Submit a code snippet, frame the review focus, attach evidence and keep a trace of the review questions you
          want a peer to ask. The goal is not auto-grading. It is disciplined preparation for 42-style feedback.
        </p>
      </section>

      <ReviewClient modules={modules} />
    </main>
  );
}
