/**
 * SourcePolicyBadge — visual trust-tier indicator for source-policy governance.
 *
 * Maps each curriculum source tier to a trust level with a color-coded badge
 * so learners can instantly see how much weight a resource carries.
 *
 * Tier mapping (from CLAUDE.md governance contract):
 *   official_42           → high   (green)  — ground truth
 *   community_docs        → medium (blue)   — explanation and mapping
 *   testers_and_tooling   → medium (teal)   — verification
 *   solution_metadata     → low    (yellow) — path mapping only
 *   blocked_solution_content → blocked (red) — blocked by default
 */

type TrustLevel = "high" | "medium" | "low" | "blocked";

type TierConfig = {
  trust: TrustLevel;
  label: string;
  icon: string;
};

const TIER_CONFIG: Record<string, TierConfig> = {
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

const FALLBACK: TierConfig = {
  trust: "low",
  label: "Unknown",
  icon: "?",
};

export function SourcePolicyBadge({ tier }: { tier: string }) {
  const config = TIER_CONFIG[tier] ?? FALLBACK;

  return (
    <span className={`spb spb--${config.trust}`} title={`Trust: ${config.trust} — ${tier}`}>
      <span className="spb-icon">{config.icon}</span>
      <span className="spb-label">{config.label}</span>
    </span>
  );
}

export function SourcePolicyLegend() {
  const levels: { trust: TrustLevel; label: string; description: string }[] = [
    { trust: "high", label: "Official", description: "Ground truth — reference baseline" },
    { trust: "medium", label: "Community / Tooling", description: "Explanation, mapping and verification" },
    { trust: "low", label: "Metadata only", description: "Path mapping — no direct content" },
    { trust: "blocked", label: "Blocked", description: "Direct solution content — blocked by default" },
  ];

  return (
    <div className="spb-legend">
      {levels.map((l) => (
        <div key={l.trust} className="spb-legend-item">
          <span className={`spb spb--${l.trust}`}>
            <span className="spb-label">{l.label}</span>
          </span>
          <span className="muted">{l.description}</span>
        </div>
      ))}
    </div>
  );
}
