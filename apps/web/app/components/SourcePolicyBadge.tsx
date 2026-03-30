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
