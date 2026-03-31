"use client";

import Link from "next/link";
import { useMemo, useState, useCallback } from "react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export type NodeState = "done" | "in_progress" | "todo";

export type GraphNodeData = {
  id: string;
  title: string;
  trackId: string;
  phase: string;
  skillCount: number;
  state: NodeState;
  prerequisites: string[];
};

type LayoutNode = GraphNodeData & { x: number; y: number; tier: number };

type Edge = {
  fromId: string;
  toId: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
};

type TrackTheme = {
  accent: string;
  surface: string;
};

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const NODE_W = 160;
const NODE_H = 56;
const TIER_GAP = 120;
const COL_GAP = 40;
const PAD = 40;

/* ------------------------------------------------------------------ */
/*  Layout algorithm                                                   */
/* ------------------------------------------------------------------ */

function computeLayout(nodes: GraphNodeData[]): {
  layout: LayoutNode[];
  edges: Edge[];
  width: number;
  height: number;
} {
  if (nodes.length === 0) return { layout: [], edges: [], width: 0, height: 0 };

  const byId = new Map(nodes.map((n) => [n.id, n]));

  // Compute tier (depth) for each node via BFS from roots
  const tierMap = new Map<string, number>();

  function tier(id: string, visited: Set<string>): number {
    if (tierMap.has(id)) return tierMap.get(id)!;
    if (visited.has(id)) return 0;
    visited.add(id);
    const node = byId.get(id);
    const deps = (node?.prerequisites ?? []).filter((d) => byId.has(d));
    if (deps.length === 0) { tierMap.set(id, 0); return 0; }
    const max = Math.max(...deps.map((d) => tier(d, visited)));
    const t = max + 1;
    tierMap.set(id, t);
    return t;
  }

  for (const n of nodes) tier(n.id, new Set());

  // Group by tier, sort within tier by original order
  const tiers = new Map<number, GraphNodeData[]>();
  for (const n of nodes) {
    const t = tierMap.get(n.id) ?? 0;
    if (!tiers.has(t)) tiers.set(t, []);
    tiers.get(t)!.push(n);
  }

  const maxTier = Math.max(...tiers.keys());

  // Compute canvas width from widest tier
  let maxRowW = 0;
  for (const [, row] of tiers) {
    const w = row.length * NODE_W + (row.length - 1) * COL_GAP;
    if (w > maxRowW) maxRowW = w;
  }
  const canvasW = Math.max(maxRowW + PAD * 2, 600);

  // Position nodes
  const layout: LayoutNode[] = [];
  for (let t = 0; t <= maxTier; t++) {
    const row = tiers.get(t) ?? [];
    const rowW = row.length * NODE_W + (row.length - 1) * COL_GAP;
    const startX = (canvasW - rowW) / 2;
    const y = t * TIER_GAP + PAD;
    for (let i = 0; i < row.length; i++) {
      layout.push({ ...row[i], x: startX + i * (NODE_W + COL_GAP), y, tier: t });
    }
  }

  // Build edges
  const posMap = new Map(layout.map((n) => [n.id, n]));
  const edges: Edge[] = [];
  for (const n of nodes) {
    for (const depId of n.prerequisites) {
      const from = posMap.get(depId);
      const to = posMap.get(n.id);
      if (from && to) {
        edges.push({
          fromId: depId,
          toId: n.id,
          x1: from.x + NODE_W / 2,
          y1: from.y + NODE_H,
          x2: to.x + NODE_W / 2,
          y2: to.y,
        });
      }
    }
  }

  const canvasH = (maxTier + 1) * TIER_GAP + PAD * 2;
  return { layout, edges, width: canvasW, height: canvasH };
}

/* ------------------------------------------------------------------ */
/*  Visual helpers                                                     */
/* ------------------------------------------------------------------ */

function nodeVisual(state: NodeState, theme: TrackTheme) {
  if (state === "done") {
    return {
      border: theme.accent,
      bg: theme.surface,
      text: theme.accent,
      label: "done",
    };
  }
  if (state === "in_progress") {
    return {
      border: "var(--shell-warning)",
      bg: "rgba(247, 190, 22, 0.08)",
      text: "var(--shell-warning)",
      label: "active",
    };
  }
  return {
    border: "var(--shell-border)",
    bg: "rgba(45, 47, 54, 0.15)",
    text: "var(--shell-dim)",
    label: "locked",
  };
}

function edgeColor(fromState: NodeState, accent: string) {
  if (fromState === "done") return accent;
  if (fromState === "in_progress") return "var(--shell-warning)";
  return "var(--shell-border)";
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function SkillGraph({
  nodes,
  themes,
}: {
  nodes: GraphNodeData[];
  themes: Record<string, TrackTheme>;
}) {
  const { layout, edges, width, height } = useMemo(() => computeLayout(nodes), [nodes]);
  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selected = selectedId ? byId.get(selectedId) ?? null : null;

  const handleSelect = useCallback((id: string) => {
    setSelectedId((prev) => (prev === id ? null : id));
  }, []);

  const handleKey = useCallback(
    (id: string, e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        handleSelect(id);
      }
    },
    [handleSelect],
  );

  if (nodes.length === 0) return null;

  const themeFor = (trackId: string) =>
    themes[trackId] ?? { accent: "var(--shell-success)", surface: "var(--shell-10)" };

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
      {/* Canvas */}
      <div
        className="relative overflow-x-auto border border-[var(--shell-border)] bg-[var(--shell-canvas)]"
        style={{
          backgroundImage:
            "radial-gradient(circle, var(--shell-border) 1px, transparent 1px)",
          backgroundSize: "20px 20px",
        }}
      >
        <svg
          width={width}
          height={height}
          className="mx-auto block"
          role="img"
          aria-label="Module dependency graph"
        >
          {/* Edges */}
          {edges.map((e) => {
            const from = byId.get(e.fromId);
            return (
              <line
                key={`${e.fromId}-${e.toId}`}
                x1={e.x1}
                y1={e.y1}
                x2={e.x2}
                y2={e.y2}
                stroke={edgeColor(from?.state ?? "todo", themeFor(from?.trackId ?? "shell").accent)}
                strokeWidth={1}
                strokeDasharray="6 4"
                strokeOpacity={0.6}
              />
            );
          })}

          {/* Nodes */}
          {layout.map((node) => {
            const theme = themeFor(node.trackId);
            const v = nodeVisual(node.state, theme);
            const isSelected = node.id === selectedId;

            return (
              <foreignObject key={node.id} x={node.x} y={node.y} width={NODE_W} height={NODE_H}>
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => handleSelect(node.id)}
                  onKeyDown={(e) => handleKey(node.id, e)}
                  className="flex h-full cursor-pointer flex-col justify-between px-3 py-2 transition-colors"
                  style={{
                    borderWidth: isSelected || node.state === "in_progress" ? 2 : 1,
                    borderStyle: "solid",
                    borderColor: isSelected ? "var(--shell-success)" : v.border,
                    backgroundColor: v.bg,
                    boxShadow: isSelected ? "0 0 0 2px var(--shell-success)" : "none",
                  }}
                >
                  <div className="flex items-start justify-between gap-1">
                    <span
                      className="font-mono text-[9px] uppercase tracking-[0.24em]"
                      style={{ color: v.text }}
                    >
                      {v.label}
                    </span>
                    <span className="font-mono text-[9px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
                      {node.skillCount}sk
                    </span>
                  </div>
                  <h3
                    className="truncate font-mono text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]"
                  >
                    {node.title}
                  </h3>
                </div>
              </foreignObject>
            );
          })}
        </svg>

        {/* Status bar */}
        <div className="flex items-center justify-between border-t border-[var(--shell-border)] px-4 py-1.5">
          <p className="font-mono text-[10px] text-[var(--shell-dim)]">
            {nodes.length} nodes // {edges.length} edges
          </p>
        </div>
      </div>

      {/* Detail sidebar */}
      <aside className="border border-[var(--shell-border)] bg-[var(--shell-panel)]">
        {selected ? (
          <NodeDetail node={selected} allNodes={nodes} themeFor={themeFor} />
        ) : (
          <div className="flex h-full items-center justify-center p-6">
            <p className="text-center font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-dim)]">
              Click a node to inspect
            </p>
          </div>
        )}
      </aside>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Node detail panel                                                  */
/* ------------------------------------------------------------------ */

function NodeDetail({
  node,
  allNodes,
  themeFor,
}: {
  node: GraphNodeData;
  allNodes: GraphNodeData[];
  themeFor: (trackId: string) => TrackTheme;
}) {
  const byId = new Map(allNodes.map((n) => [n.id, n]));
  const prereqs = node.prerequisites.map((id) => byId.get(id)).filter(Boolean) as GraphNodeData[];
  const dependents = allNodes.filter((n) => n.prerequisites.includes(node.id));
  const theme = themeFor(node.trackId);
  const v = nodeVisual(node.state, theme);

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* Section label pattern from Figma */}
      <div>
        <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Module</p>
        <p className="mt-1 font-mono text-sm font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
          {node.title}
        </p>
      </div>

      <div>
        <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Status</p>
        <p className="mt-1 font-mono text-xs font-bold uppercase" style={{ color: v.text }}>
          {v.label}
        </p>
      </div>

      <div>
        <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Skills</p>
        <p className="mt-1 font-mono text-xs text-[var(--shell-muted)]">
          {node.skillCount} skills // {node.phase} phase
        </p>
      </div>

      {prereqs.length > 0 && (
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Prerequisites</p>
          <div className="mt-1 space-y-0.5">
            {prereqs.map((dep, i) => (
              <p key={dep.id} className="font-mono text-[10px] leading-4 text-[var(--shell-dim)]">
                <span>{i === prereqs.length - 1 ? "└── " : "├── "}</span>
                <span className={dep.state === "done" ? "text-[var(--shell-success)]" : ""}>
                  {dep.title}
                </span>
                {dep.state === "done" && (
                  <span className="ml-1 text-[var(--shell-success)]">[DONE]</span>
                )}
              </p>
            ))}
          </div>
        </div>
      )}

      {dependents.length > 0 && (
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Unlocks</p>
          <div className="mt-1 space-y-0.5">
            {dependents.map((dep) => (
              <p key={dep.id} className="font-mono text-[10px] leading-4 text-[var(--shell-dim)]">
                <span className="text-[var(--shell-muted)]">→ </span>
                {dep.title}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Action */}
      <div className="mt-auto pt-2">
        {node.state === "todo" ? (
          <p className="font-mono text-[10px] text-[var(--shell-dim)]">Complete prerequisites to unlock</p>
        ) : (
          <Link
            href={`/modules/${node.id}`}
            className="flex h-8 items-center justify-center font-mono text-[10px] font-bold uppercase tracking-[0.24em] transition-colors"
            style={{
              backgroundColor: node.state === "in_progress" ? "var(--shell-warning)" : theme.accent,
              color: "var(--shell-canvas)",
            }}
          >
            {node.state === "in_progress" ? "[ CONTINUE ]" : "[ REVIEW ]"}
          </Link>
        )}
      </div>
    </div>
  );
}
