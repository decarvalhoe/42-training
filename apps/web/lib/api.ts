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
  reference_note?: string;
  subject_refs?: SubjectRef[];
};

export type TrackItem = {
  id: string;
  title: string;
  summary: string;
  why_it_matters: string;
  modules: ModuleItem[];
};

export type ReferenceItem = {
  label: string;
  url: string;
  tier: string;
  confidence?: string;
  usage?: string;
  note?: string;
};

export type SubjectRef = {
  label: string;
  document_title: string;
  url: string;
  mirror_path?: string;
  tier: string;
  confidence: string;
  coverage: string;
  note?: string;
};

export type QualityTool = {
  id: string;
  label: string;
  url: string;
  language: string;
  kind: string;
  authority: string;
  role: string;
  note?: string;
};

export type QualityEquivalent = {
  language: string;
  positioning: string;
  quality_contract: string;
  automated_gates: string[];
  human_review_focus: string[];
};

export type DashboardData = {
  curriculum: {
    metadata: {
      campus: string;
      updated_on: string;
      status?: string;
      reference_posture?: string;
    };
    source_policy: {
      tiers: Array<{ id: string; label: string; allowed_usage: string }>;
      confidence_model?: Array<{ level: string; meaning: string }>;
    };
    reference_stack: {
      official_documents: ReferenceItem[];
      official_document_mirrors: ReferenceItem[];
      quality_stack: QualityTool[];
      quality_equivalents: QualityEquivalent[];
    };
    tracks: TrackItem[];
    bridges: Array<{ id: string; title: string; recommended_modules: string[] }>;
    recommended_resources?: Array<{ label: string; url: string; tier: string }>;
    curriculum_mapping: {
      legacy_common_core: {
        summary: string;
        preserved_dimensions?: string[];
      };
      new_common_core_interpretation: {
        summary: string;
        confidence: string;
        note: string;
        milestones?: Array<{ milestone: string; projects: string[]; confidence: string }>;
        style_analogies?: Array<{ legacy_anchor: string; new_project: string; rationale: string }>;
        predicted_project_models?: Array<{
          id: string;
          title: string;
          milestone: string;
          confidence: string;
          legacy_style_anchors: string[];
          predicted_subject_style: string;
          predicted_constraints: string[];
          predicted_deliverables: string[];
          predicted_core_skills: string[];
        }>;
      };
      synthesis?: {
        summary: string;
        principles: string[];
      };
    };
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
      updated_on: "2026-03-29",
      status: "reference-refresh",
      reference_posture: "official public documents first, verified mirrors second, community tooling as verification only",
    },
    source_policy: {
      tiers: [
        { id: "official_42", label: "Official 42 sources", allowed_usage: "ground_truth" },
        { id: "community_docs", label: "Community docs", allowed_usage: "explanation_and_mapping" },
        { id: "testers_and_tooling", label: "Testers and tooling", allowed_usage: "verification" },
        { id: "solution_metadata", label: "Solution metadata", allowed_usage: "path_mapping_only" },
        { id: "blocked_solution_content", label: "Direct solution content", allowed_usage: "blocked_by_default" }
      ],
      confidence_model: [
        { level: "high", meaning: "Official public page or official normative PDF." },
        { level: "medium", meaning: "Verified mirror or staff-corroborated signal." },
        { level: "interpreted", meaning: "Inference kept explicit as interpretation." }
      ],
    },
    reference_stack: {
      official_documents: [
        {
          label: "42 Lausanne - pedagogie",
          url: "https://42lausanne.ch/pedagogie-42/",
          tier: "official_42",
          confidence: "high",
          usage: "campus pedagogy and learning model"
        },
        {
          label: "42 Lausanne - IA",
          url: "https://42lausanne.ch/ia/",
          tier: "official_42",
          confidence: "high",
          usage: "public signal that AI is now inside the Lausanne positioning"
        },
        {
          label: "The Norm v4.1 (English PDF)",
          url: "https://github.com/42School/norminette/blob/master/pdf/en.norm.pdf",
          tier: "official_42",
          confidence: "high",
          usage: "absolute code-quality and pedagogical reference for C projects"
        }
      ],
      official_document_mirrors: [
        {
          label: "Ninjarsenic/42-Tronc_commun",
          url: "https://github.com/Ninjarsenic/42-Tronc_commun",
          tier: "official_document_mirrors",
          confidence: "medium",
          note: "Private mirror of Common Core subjects."
        },
        {
          label: "Ninjarsenic/42-piscine",
          url: "https://github.com/Ninjarsenic/42-piscine",
          tier: "official_document_mirrors",
          confidence: "medium",
          note: "Private mirror of official Piscine assets."
        }
      ],
      quality_stack: [
        {
          id: "norminette",
          label: "norminette",
          url: "https://github.com/42school/norminette",
          language: "c",
          kind: "official_checker",
          authority: "official_tool",
          role: "Objective Norm checks."
        },
        {
          id: "francinette",
          label: "francinette",
          url: "https://github.com/xicodomingues/francinette",
          language: "c",
          kind: "community_local_moulinette",
          authority: "verification_only",
          role: "Local make + norm + tester battery.",
          note: "Archived upstream."
        },
        {
          id: "ruff",
          label: "ruff",
          url: "https://github.com/astral-sh/ruff",
          language: "python",
          kind: "lint_and_format",
          authority: "equivalent_quality_gate",
          role: "Formatting and lint baseline for Python."
        },
        {
          id: "shellcheck",
          label: "ShellCheck",
          url: "https://www.shellcheck.net/",
          language: "bash",
          kind: "lint",
          authority: "equivalent_quality_gate",
          role: "Quoting and portability guardrails for shell."
        }
      ],
      quality_equivalents: [
        {
          language: "c",
          positioning: "Absolute reference track.",
          quality_contract: "The Norm plus norminette plus project-specific testers.",
          automated_gates: ["norminette", "cc -Wall -Wextra -Werror", "tester suites"],
          human_review_focus: ["clarity", "defense readiness", "subjective Norm items"]
        },
        {
          language: "python",
          positioning: "Equivalent rigor, not C mimicry.",
          quality_contract: "Short explicit functions, typed boundaries, readable flow, test coverage.",
          automated_gates: ["ruff check", "ruff format", "mypy", "pytest"],
          human_review_focus: ["algorithmic explanation", "controlled abstraction", "debuggability"]
        },
        {
          language: "bash",
          positioning: "Terminal-first discipline.",
          quality_contract: "Readable scripts, explicit quoting, small units, fail-fast habits.",
          automated_gates: ["shellcheck", "shfmt", "smoke scripts"],
          human_review_focus: ["pipeline clarity", "error handling", "debugging under shell constraints"]
        }
      ]
    },
    tracks: [
      {
        id: "shell",
        title: "Shell 0 to Hero",
        summary: "Linux-first recovery track before Piscine pressure.",
        why_it_matters: "Rebuild confidence, command fluency and process awareness.",
        modules: [
          {
            id: "shell-basics",
            title: "Navigation and files",
            phase: "foundation",
            skills: ["pwd", "ls", "cd", "cp"],
            deliverable: "Navigate and manipulate files with confidence.",
            reference_note: "Anchored to the exact Shell00 official subject mirror.",
          },
          {
            id: "shell-streams",
            title: "Redirections and pipes",
            phase: "foundation",
            skills: ["stdin", "stdout", "pipe"],
            deliverable: "Chain commands effectively.",
            reference_note: "Extracted from the broader Shell01 official subject."
          }
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
    ],
    recommended_resources: [
      {
        label: "42 Lausanne - pedagogie",
        url: "https://42lausanne.ch/pedagogie-42/",
        tier: "official_42"
      },
      {
        label: "The Norm v4.1 (English PDF)",
        url: "https://github.com/42School/norminette/blob/master/pdf/en.norm.pdf",
        tier: "official_42"
      },
      {
        label: "Ninjarsenic/42-Tronc_commun",
        url: "https://github.com/Ninjarsenic/42-Tronc_commun",
        tier: "community_docs"
      }
    ],
    curriculum_mapping: {
      legacy_common_core: {
        summary: "Historically C and Unix heavy, then concurrency, graphics, C++, network and devops.",
        preserved_dimensions: ["terminal autonomy", "memory rigor", "oral defense readiness"]
      },
      new_common_core_interpretation: {
        summary: "Algorithms earlier, Python earlier, AI inside the common core.",
        confidence: "medium",
        note: "Project naming is still partially interpreted from mirrored packs and infographic signals.",
        milestones: [
          { milestone: "M1", projects: ["libft", "push_swap", "printf", "get_next_line"], confidence: "medium" },
          { milestone: "M2", projects: ["piscine python", "a maze ing", "born2beroot"], confidence: "interpreted" }
        ],
        style_analogies: [
          {
            legacy_anchor: "C Piscine modules",
            new_project: "piscine python",
            rationale: "Bootcamp role preserved, but translated to Python."
          }
        ],
        predicted_project_models: [
          {
            id: "piscine-python",
            title: "piscine python",
            milestone: "M2",
            confidence: "interpreted",
            legacy_style_anchors: ["C Piscine modules C00-C13", "Shell00", "Shell01"],
            predicted_subject_style: "Small escalating exercises with strict mastery of foundations.",
            predicted_constraints: ["small scripts", "stdlib only", "explicit functions"],
            predicted_deliverables: ["ex00..exNN scripts", "tiny CLIs", "simple tests"],
            predicted_core_skills: ["syntax", "functions", "strings", "objects"]
          }
        ]
      },
      synthesis: {
        summary: "Keep old Common Core rigor while preparing for the Python and AI branch.",
        principles: [
          "Preserve legacy C rigor.",
          "Make Python and Bash quality expectations explicit.",
          "Surface confidence levels for interpreted curriculum elements."
        ]
      }
    }
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

// --- Tmux session types (Issue #178) ---

export type TmuxSession = {
  name: string;
  status: "active" | "idle";
  created_at: string;
  last_activity: string;
  windows: number;
  attached: boolean;
};

export type TmuxSessionsData = {
  sessions: TmuxSession[];
  total: number;
};

export async function getTmuxSessions(): Promise<TmuxSessionsData> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  try {
    const response = await fetch(`${apiUrl}/api/v1/tmux/sessions`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`API returned ${response.status}`);
    }
    return (await response.json()) as TmuxSessionsData;
  } catch {
    return { sessions: [], total: 0 };
  }
}

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
