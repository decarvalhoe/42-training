import type { DashboardData, ModuleItem, TmuxSession, TrackItem } from "@/lib/api";

export type ModuleState = "done" | "in_progress" | "todo";
export type LearnerMode = "empty" | "active" | "returning";

export type ModuleWithContext = {
  module: ModuleItem;
  trackId: string;
  trackTitle: string;
  trackSummary: string;
  state: ModuleState;
};

export type TrackStats = {
  id: string;
  title: string;
  summary: string;
  totalModules: number;
  completedModules: number;
  inProgressModules: number;
  percentComplete: number;
  totalSkills: number;
  activeModule: ModuleItem | null;
  nextReadyModule: ModuleItem | null;
};

type TrackTheme = {
  label: string;
  accent: string;
  surface: string;
  border: string;
};

const TRACK_THEMES: Record<string, TrackTheme> = {
  shell: {
    label: "Shell",
    accent: "var(--shell-success)",
    surface: "var(--shell-10)",
    border: "var(--shell)",
  },
  c: {
    label: "C",
    accent: "var(--c)",
    surface: "var(--c-10)",
    border: "var(--c-20)",
  },
  python_ai: {
    label: "Python + AI",
    accent: "var(--python)",
    surface: "var(--python-10)",
    border: "var(--python-20)",
  },
};

export function deriveModuleState(
  moduleId: string,
  trackId: string,
  activeTrack: string,
  activeModule: string,
  modules: ModuleItem[],
): ModuleState {
  if (trackId !== activeTrack) {
    return "todo";
  }

  if (moduleId === activeModule) {
    return "in_progress";
  }

  const activeIndex = modules.findIndex((module) => module.id === activeModule);
  const currentIndex = modules.findIndex((module) => module.id === moduleId);

  if (activeIndex === -1 || currentIndex === -1) {
    return "todo";
  }

  return currentIndex < activeIndex ? "done" : "todo";
}

export function flattenModules(
  tracks: TrackItem[],
  activeTrack: string,
  activeModule: string,
): ModuleWithContext[] {
  return tracks.flatMap((track) =>
    track.modules.map((module) => ({
      module,
      trackId: track.id,
      trackTitle: track.title,
      trackSummary: track.summary,
      state: deriveModuleState(module.id, track.id, activeTrack, activeModule, track.modules),
    })),
  );
}

export function countSkills(tracks: TrackItem[]) {
  return tracks.reduce((sum, track) => sum + track.modules.reduce((value, module) => value + module.skills.length, 0), 0);
}

export function findNextReadyModule(modules: ModuleWithContext[]) {
  const stateById = new Map(modules.map((entry) => [entry.module.id, entry.state]));

  return modules.find((entry) => {
    if (entry.state !== "todo") {
      return false;
    }

    const prerequisites = entry.module.prerequisites ?? [];
    return prerequisites.every((prerequisiteId) => stateById.get(prerequisiteId) === "done");
  }) ?? null;
}

export function buildTrackStats(
  track: TrackItem,
  activeTrack: string,
  activeModule: string,
): TrackStats {
  const completedModules = track.modules.filter(
    (module) => deriveModuleState(module.id, track.id, activeTrack, activeModule, track.modules) === "done",
  ).length;

  const inProgressModule =
    track.modules.find(
      (module) => deriveModuleState(module.id, track.id, activeTrack, activeModule, track.modules) === "in_progress",
    ) ?? null;

  const trackContext = flattenModules([track], activeTrack, activeModule);
  const nextReadyModule = findNextReadyModule(trackContext)?.module ?? null;

  return {
    id: track.id,
    title: track.title,
    summary: track.summary,
    totalModules: track.modules.length,
    completedModules,
    inProgressModules: inProgressModule === null ? 0 : 1,
    percentComplete: track.modules.length === 0 ? 0 : Math.round((completedModules / track.modules.length) * 100),
    totalSkills: track.modules.reduce((sum, module) => sum + module.skills.length, 0),
    activeModule: inProgressModule,
    nextReadyModule,
  };
}

export function getLearnerMode(modules: ModuleWithContext[]): LearnerMode {
  const hasCompleted = modules.some((entry) => entry.state === "done");
  const hasActive = modules.some((entry) => entry.state === "in_progress");

  if (hasActive) {
    return "active";
  }

  if (hasCompleted) {
    return "returning";
  }

  return "empty";
}

export function summarizeSessions(sessions: TmuxSession[]) {
  const active = sessions.filter((session) => session.status === "active").length;
  const idle = sessions.filter((session) => session.status === "idle").length;
  const primary = sessions[0] ?? null;

  return {
    total: sessions.length,
    active,
    idle,
    primary,
  };
}

export function getTrackTheme(trackId: string): TrackTheme {
  return TRACK_THEMES[trackId] ?? TRACK_THEMES.shell;
}

export function getLearningContext(data: DashboardData) {
  const activeTrack = data.progression.learning_plan?.active_course ?? data.curriculum.tracks[0]?.id ?? "shell";
  const activeModule = data.progression.learning_plan?.active_module ?? "";
  const modules = flattenModules(data.curriculum.tracks, activeTrack, activeModule);

  return {
    activeTrack,
    activeModule,
    modules,
    learnerMode: getLearnerMode(modules),
    nextReadyModule: findNextReadyModule(modules),
    trackStats: data.curriculum.tracks.map((track) => buildTrackStats(track, activeTrack, activeModule)),
  };
}
