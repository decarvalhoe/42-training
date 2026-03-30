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
    <ReviewClient modules={modules} />
  );
}
