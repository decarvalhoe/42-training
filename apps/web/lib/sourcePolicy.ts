export const SOURCE_POLICY_TIER_IDS = [
  "official_42",
  "community_docs",
  "testers_and_tooling",
  "solution_metadata",
  "blocked_solution_content",
] as const;

export type SourcePolicyTierId = (typeof SOURCE_POLICY_TIER_IDS)[number];
export type SourcePolicyBadgeTrust = "high" | "medium" | "low" | "blocked";

export type SourcePolicyTierConfig = {
  trust: SourcePolicyBadgeTrust;
  label: string;
  icon: string;
};

export const SOURCE_POLICY_TIER_CONFIG: Record<SourcePolicyTierId, SourcePolicyTierConfig> = {
  official_42: {
    trust: "high",
    label: "Official",
    icon: "\u2713",
  },
  community_docs: {
    trust: "medium",
    label: "Community",
    icon: "\u25CB",
  },
  testers_and_tooling: {
    trust: "medium",
    label: "Tooling",
    icon: "\u25CB",
  },
  solution_metadata: {
    trust: "low",
    label: "Metadata only",
    icon: "\u25B3",
  },
  blocked_solution_content: {
    trust: "blocked",
    label: "Blocked",
    icon: "\u2717",
  },
};

export function isKnownSourcePolicyTier(tier: string): tier is SourcePolicyTierId {
  return Object.hasOwn(SOURCE_POLICY_TIER_CONFIG, tier);
}

export function isDisplayableSourcePolicyTier(
  tier: string,
): tier is Exclude<SourcePolicyTierId, "blocked_solution_content"> {
  return isKnownSourcePolicyTier(tier) && tier !== "blocked_solution_content";
}
