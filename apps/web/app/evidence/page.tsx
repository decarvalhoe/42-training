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
    <EvidenceClient modules={modules} />
  );
}
