import {
  SOURCE_POLICY_TIER_CONFIG,
  type SourcePolicyBadgeTrust,
} from "@/lib/sourcePolicy";

const FALLBACK: { trust: SourcePolicyBadgeTrust; label: string; icon: string } = {
  trust: "low",
  label: "Unknown",
  icon: "?",
};

export function SourcePolicyBadge({ tier }: { tier: string }) {
  const config = SOURCE_POLICY_TIER_CONFIG[tier as keyof typeof SOURCE_POLICY_TIER_CONFIG] ?? FALLBACK;

  return (
    <span className={`spb spb--${config.trust}`} title={`Trust: ${config.trust} — ${tier}`}>
      <span className="spb-icon">{config.icon}</span>
      <span className="spb-label">{config.label}</span>
    </span>
  );
}

export function SourcePolicyLegend() {
  const levels: { trust: SourcePolicyBadgeTrust; label: string; description: string }[] = [
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
