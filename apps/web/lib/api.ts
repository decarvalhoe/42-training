export type ModuleResource = {
  label: string;
  url: string;
  tier: string;
  why?: string;
};

export type ModuleItem = {
  id: string;
  title: string;
  phase: string;
  skills: string[];
  deliverable: string;
  objectives?: string[];
  exit_criteria?: string[];
  resources?: ModuleResource[];
  estimated_hours?: number;
  prerequisites?: string[];
};

export type TrackItem = {
  id: string;
  title: string;
  summary: string;
  why_it_matters: string;
  modules: ModuleItem[];
};

export type DashboardData = {
  curriculum: {
    metadata: {
      campus: string;
      updated_on: string;
    };
    source_policy: {
      tiers: Array<{ id: string; label: string; allowed_usage: string }>;
    };
    tracks: TrackItem[];
    bridges: Array<{ id: string; title: string; recommended_modules: string[] }>;
    recommended_resources?: Array<{ label: string; url: string; tier: string }>;
  };
  progression: {
    learning_plan?: {
      active_course?: string;
      active_module?: string;
      pace_mode?: string;
      profile?: string;
    };
    progress?: {
      current_exercise?: string;
      current_step?: string;
      completed?: string[];
      in_progress?: string[];
      todo?: string[];
    };
    next_command?: string;
  };
};

export type AnalyticsSummary = {
  total_events: number;
  module_completions: number;
  average_completion_minutes: number;
  checkpoint_success_rate: number;
  mentor_queries: number;
  defenses_started: number;
};

export type AnalyticsChartRow = {
  module_id: string;
  module_title: string;
  track_id: string;
  phase: string;
  value: number;
  count: number;
  suffix: string;
};

export type AnalyticsData = {
  summary: AnalyticsSummary;
  modules_completed: AnalyticsChartRow[];
  average_time: AnalyticsChartRow[];
  success_rate: AnalyticsChartRow[];
};

const fallbackData: DashboardData = {
  curriculum: {
    metadata: {
      campus: "42 Lausanne",
      updated_on: "2026-03-27",
    },
    source_policy: {
      tiers: [
        { id: "official_42", label: "Official 42 sources", allowed_usage: "ground_truth" },
        { id: "community_docs", label: "Community docs", allowed_usage: "explanation_and_mapping" },
        { id: "testers_and_tooling", label: "Testers and tooling", allowed_usage: "verification" },
        { id: "solution_metadata", label: "Solution metadata", allowed_usage: "path_mapping_only" },
        { id: "blocked_solution_content", label: "Direct solution content", allowed_usage: "blocked_by_default" }
      ],
    },
    tracks: [
      {
        id: "shell",
        title: "Shell 0 to Hero",
        summary: "Linux-first recovery track before Piscine pressure.",
        why_it_matters: "Rebuild confidence, command fluency and process awareness.",
        modules: [
          { id: "shell-basics", title: "Navigation and files", phase: "foundation", skills: ["pwd", "ls", "cd", "cp"], deliverable: "Navigate and manipulate files with confidence." },
          { id: "shell-streams", title: "Redirections and pipes", phase: "foundation", skills: ["stdin", "stdout", "pipe"], deliverable: "Chain commands effectively." }
        ],
      },
      {
        id: "c",
        title: "C / Core 42",
        summary: "Low-level rigor track aligned with the core 42 mindset.",
        why_it_matters: "Build algorithmic reasoning and memory discipline.",
        modules: [
          { id: "c-basics", title: "Syntax and control flow", phase: "foundation", skills: ["if", "while", "functions"], deliverable: "Write and compile small programs." },
          { id: "c-memory", title: "Pointers and memory", phase: "foundation", skills: ["pointers", "malloc", "free"], deliverable: "Understand memory choices and avoid basic leaks." }
        ],
      },
      {
        id: "python_ai",
        title: "Python + AI",
        summary: "Python foundations plus the modern AI axis.",
        why_it_matters: "Prepare for the new branch while keeping fundamentals intact.",
        modules: [
          { id: "python-basics", title: "Python foundations", phase: "foundation", skills: ["conditions", "loops", "functions"], deliverable: "Write small scripts confidently." },
          { id: "ai-rag-agents", title: "AI, RAG and agent literacy", phase: "advanced", skills: ["retrieval", "evaluation", "source policy"], deliverable: "Use AI with discipline." }
        ],
      }
    ],
    bridges: [
      { id: "before_piscine", title: "Before the Piscine", recommended_modules: ["shell:shell-basics", "c:c-basics"] },
      { id: "before_new_common_core", title: "Before the new common core", recommended_modules: ["c:c-memory", "python_ai:ai-rag-agents"] }
    ]
  },
  progression: {
    learning_plan: {
      active_course: "shell",
      active_module: "shell-basics",
      pace_mode: "self_paced",
      profile: "Experienced IT professional returning to hands-on coding"
    },
    progress: {
      current_exercise: "Exercice 2: Manipulation fichiers",
      current_step: "2.4 - Copier et supprimer fichiers",
      completed: ["pwd", "ls -la", "mkdir", "mv", "cd", "touch", "cat"],
      in_progress: ["cp - Copier fichiers"],
      todo: ["rm", "pipes", "grep", "find", "chmod"]
    },
    next_command: "cp hello.txt test.txt"
  }
};

const fallbackAnalyticsData: AnalyticsData = {
  summary: {
    total_events: 24,
    module_completions: 7,
    average_completion_minutes: 48.5,
    checkpoint_success_rate: 71.4,
    mentor_queries: 11,
    defenses_started: 2,
  },
  modules_completed: [
    {
      module_id: "shell-basics",
      module_title: "Navigation and files",
      track_id: "shell",
      phase: "foundation",
      value: 4,
      count: 4,
      suffix: " completions",
    },
    {
      module_id: "c-basics",
      module_title: "Syntax and control flow",
      track_id: "c",
      phase: "foundation",
      value: 2,
      count: 2,
      suffix: " completions",
    },
    {
      module_id: "python-basics",
      module_title: "Python foundations",
      track_id: "python_ai",
      phase: "foundation",
      value: 1,
      count: 1,
      suffix: " completions",
    }
  ],
  average_time: [
    {
      module_id: "c-basics",
      module_title: "Syntax and control flow",
      track_id: "c",
      phase: "foundation",
      value: 72,
      count: 2,
      suffix: " min",
    },
    {
      module_id: "python-basics",
      module_title: "Python foundations",
      track_id: "python_ai",
      phase: "foundation",
      value: 55,
      count: 1,
      suffix: " min",
    },
    {
      module_id: "shell-basics",
      module_title: "Navigation and files",
      track_id: "shell",
      phase: "foundation",
      value: 38,
      count: 4,
      suffix: " min",
    }
  ],
  success_rate: [
    {
      module_id: "shell-basics",
      module_title: "Navigation and files",
      track_id: "shell",
      phase: "foundation",
      value: 83.3,
      count: 6,
      suffix: "%",
    },
    {
      module_id: "python-basics",
      module_title: "Python foundations",
      track_id: "python_ai",
      phase: "foundation",
      value: 75,
      count: 4,
      suffix: "%",
    },
    {
      module_id: "c-basics",
      module_title: "Syntax and control flow",
      track_id: "c",
      phase: "foundation",
      value: 60,
      count: 5,
      suffix: "%",
    }
  ]
};

export async function getDashboardData(): Promise<DashboardData> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    const response = await fetch(`${apiUrl}/api/v1/dashboard`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    return (await response.json()) as DashboardData;
  } catch {
    return fallbackData;
  }
}

export async function getAnalyticsData(): Promise<AnalyticsData> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    const response = await fetch(`${apiUrl}/api/v1/analytics/dashboard`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    return (await response.json()) as AnalyticsData;
  } catch {
    return fallbackAnalyticsData;
  }
}
