import { redirect } from "next/navigation";

import { getDashboardData } from "@/lib/api";

export default async function ModulesIndexPage() {
  const data = await getDashboardData();
  const activeTrack = data.progression.learning_plan?.active_course ?? "shell";
  const activeModule = data.progression.learning_plan?.active_module;
  const preferredTrack =
    data.curriculum.tracks.find((track) => track.id === activeTrack) ?? data.curriculum.tracks[0];
  const fallbackModule = preferredTrack?.modules[0] ?? data.curriculum.tracks[0]?.modules[0];

  if (activeModule) {
    redirect(`/modules/${activeModule}`);
  }

  if (fallbackModule) {
    redirect(`/modules/${fallbackModule.id}`);
  }

  redirect("/dashboard");
}
