import { type SourcePolicyBadgeTrust } from "@/lib/sourcePolicy";

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
