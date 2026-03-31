import Link from "next/link";

import { getDashboardData } from "@/lib/api";
import type { ModuleItem, TrackItem } from "@/lib/api";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

type ModuleState = "done" | "in_progress" | "locked" | "available";

function deriveModuleState(
  moduleId: string,
  trackId: string,
  activeTrack: string | undefined,
  activeModule: string | undefined,
  modules: ModuleItem[],
): ModuleState {
  if (trackId !== activeTrack) return "locked";
  if (moduleId === activeModule) return "in_progress";
  const activeIdx = modules.findIndex((m) => m.id === activeModule);
  const currentIdx = modules.findIndex((m) => m.id === moduleId);
  if (activeIdx === -1) return currentIdx === 0 ? "available" : "locked";
  if (currentIdx < activeIdx) return "done";
  if (currentIdx === activeIdx + 1) return "available";
  return "locked";
}

const PHASE_ORDER: Record<string, number> = {
  foundation: 0,
  practice: 1,
  core: 2,
  advanced: 3,
};

const TRACK_TAB_COLORS: Record<string, { color: string; label: string }> = {
  shell: { color: "var(--shell-success)", label: "SHELL" },
  c: { color: "var(--c)", label: "C" },
  python_ai: { color: "var(--python)", label: "PYTHON+AI" },
};

/* ------------------------------------------------------------------ */
/*  SVG talent tree layout engine                                      */
/* ------------------------------------------------------------------ */

const NODE_W = 130;
const NODE_H = 29;
const TIER_GAP_Y = 120;
const NODE_GAP_X = 40;
const CANVAS_PAD = 40;

type LayoutNode = {
  id: string;
  label: string;
  state: ModuleState;
  phase: string;
  x: number;
  y: number;
  prerequisites: string[];
};

function layoutTree(
  modules: ModuleItem[],
  trackId: string,
  activeTrack: string | undefined,
  activeModule: string | undefined,
): { nodes: LayoutNode[]; width: number; height: number } {
  const phases = [...new Set(modules.map((m) => m.phase))].sort(
    (a, b) => (PHASE_ORDER[a] ?? 99) - (PHASE_ORDER[b] ?? 99),
  );

  const nodes: LayoutNode[] = [];
  let maxX = 0;

  phases.forEach((phase, tierIdx) => {
    const tierModules = modules.filter((m) => m.phase === phase);
    const tierWidth = tierModules.length * (NODE_W + NODE_GAP_X) - NODE_GAP_X;
    const startX = CANVAS_PAD + Math.max(0, (600 - tierWidth) / 2);
    const y = CANVAS_PAD + tierIdx * TIER_GAP_Y;

    tierModules.forEach((mod, idx) => {
      const x = startX + idx * (NODE_W + NODE_GAP_X);
      maxX = Math.max(maxX, x + NODE_W);
      nodes.push({
        id: mod.id,
        label: mod.title,
        state: deriveModuleState(mod.id, trackId, activeTrack, activeModule, modules),
        phase,
        x,
        y,
        prerequisites: mod.prerequisites ?? [],
      });
    });
  });

  return {
    nodes,
    width: Math.max(maxX + CANVAS_PAD, 700),
    height: CANVAS_PAD * 2 + (phases.length - 1) * TIER_GAP_Y + NODE_H,
  };
}

/* ------------------------------------------------------------------ */
/*  SVG components                                                     */
/* ------------------------------------------------------------------ */

function nodeColor(state: ModuleState): { stroke: string; fill: string; text: string } {
  switch (state) {
    case "done":
      return {
        stroke: "var(--shell-success)",
        fill: "rgba(0,224,110,0.08)",
        text: "var(--shell-success)",
      };
    case "in_progress":
      return {
        stroke: "var(--shell-warning)",
        fill: "rgba(247,190,22,0.08)",
        text: "var(--shell-warning)",
      };
    case "available":
      return {
        stroke: "var(--shell-border-strong)",
        fill: "rgba(58,61,70,0.15)",
        text: "var(--shell-ink)",
      };
    case "locked":
      return {
        stroke: "var(--shell-border)",
        fill: "rgba(45,47,54,0.15)",
        text: "var(--shell-dim)",
      };
  }
}

function edgeColor(fromState: ModuleState, toState: ModuleState): string {
  if (fromState === "done" && toState === "done") return "var(--shell-success)";
  if (fromState === "done" && toState === "in_progress") return "var(--shell-warning)";
  return "var(--shell-border)";
}

function TreeSvg({
  nodes,
  width,
  height,
}: {
  nodes: LayoutNode[];
  width: number;
  height: number;
}) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  /* Collect edges from prerequisites */
  const edges: { from: LayoutNode; to: LayoutNode }[] = [];
  for (const node of nodes) {
    for (const prereqId of node.prerequisites) {
      const parent = nodeMap.get(prereqId);
      if (parent) edges.push({ from: parent, to: node });
    }
  }

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="talent-tree-svg"
      preserveAspectRatio="xMidYMin meet"
    >
      {/* Edges */}
      {edges.map((e) => {
        const x1 = e.from.x + NODE_W / 2;
        const y1 = e.from.y + NODE_H;
        const x2 = e.to.x + NODE_W / 2;
        const y2 = e.to.y;
        const color = edgeColor(e.from.state, e.to.state);
        return (
          <line
            key={`${e.from.id}-${e.to.id}`}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke={color}
            strokeWidth={1}
            opacity={0.6}
          />
        );
      })}

      {/* Nodes */}
      {nodes.map((node) => {
        const c = nodeColor(node.state);
        return (
          <g key={node.id}>
            <a href={`/modules/${node.id}`}>
              <rect
                x={node.x}
                y={node.y}
                width={NODE_W}
                height={NODE_H}
                fill={c.fill}
                stroke={c.stroke}
                strokeWidth={node.state === "in_progress" ? 2 : 1}
              />
              <text
                x={node.x + NODE_W / 2}
                y={node.y + NODE_H / 2 + 1}
                textAnchor="middle"
                dominantBaseline="central"
                fill={c.text}
                fontFamily="var(--font-mono)"
                fontSize={10}
                fontWeight={node.state === "in_progress" ? 700 : 400}
              >
                {node.label.length > 16 ? node.label.slice(0, 15) + "…" : node.label}
              </text>
            </a>
          </g>
        );
      })}
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Track tab + tree composite                                         */
/* ------------------------------------------------------------------ */

function TrackTreeSection({
  tracks,
  activeTrack,
  activeModule,
}: {
  tracks: TrackItem[];
  activeTrack: string | undefined;
  activeModule: string | undefined;
}) {
  const layouts = tracks.map((track) => ({
    track,
    ...layoutTree(track.modules, track.id, activeTrack, activeModule),
  }));

  return (
    <section className="talent-graph-section">
      {/* Track tabs */}
      <div className="talent-tabs">
        {tracks.map((track) => {
          const cfg = TRACK_TAB_COLORS[track.id];
          const isActive = track.id === activeTrack;
          return (
            <Link
              key={track.id}
              href={`/tracks#${track.id}`}
              className={`talent-tab${isActive ? " talent-tab--active" : ""}`}
              style={{ "--tab-color": cfg?.color ?? "var(--accent)" } as React.CSSProperties}
            >
              [ {cfg?.label ?? track.id.toUpperCase()} ]
            </Link>
          );
        })}
      </div>

      {/* SVG trees */}
      {layouts.map(({ track, nodes, width, height }) => {
        const doneCount = nodes.filter((n) => n.state === "done").length;
        const pct = nodes.length > 0 ? Math.round((doneCount / nodes.length) * 100) : 0;
        return (
          <article key={track.id} id={track.id} className="talent-tree-canvas">
            <div className="talent-tree-track-header">
              <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.28em] text-[var(--shell-success)]">
                {track.id}
              </span>
              <span className="font-mono text-[10px] text-[var(--shell-muted)]">
                {doneCount}/{nodes.length} modules &middot; {pct}%
              </span>
            </div>
            <div className="talent-tree-overflow">
              <TreeSvg nodes={nodes} width={width} height={height} />
            </div>
          </article>
        );
      })}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Legend                                                              */
/* ------------------------------------------------------------------ */

function Legend() {
  const items: { state: ModuleState; icon: string; label: string }[] = [
    { state: "done", icon: "◆", label: "Done" },
    { state: "in_progress", icon: "▶", label: "In progress" },
    { state: "available", icon: "○", label: "Available" },
    { state: "locked", icon: "◇", label: "Locked" },
  ];

  return (
    <div className="talent-legend">
      {items.map((item) => (
        <span key={item.state}>
          <span
            className="talent-legend-icon"
            style={{ color: nodeColor(item.state).stroke }}
          >
            {item.icon}
          </span>{" "}
          {item.label}
        </span>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page                                                               */
/* ------------------------------------------------------------------ */

export default async function TracksPage() {
  const data = await getDashboardData();
  const { curriculum, progression } = data;
  const activeTrack = progression.learning_plan?.active_course;
  const activeModule = progression.learning_plan?.active_module;

  const totalModules = curriculum.tracks.reduce((sum, t) => sum + t.modules.length, 0);

  return (
    <main className="page-shell">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <Link href="/">Dashboard</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Tracks</span>
      </nav>

      <section className="panel talent-hero">
        <p className="eyebrow">Track Explorer</p>
        <h1>RPG Talent Tree</h1>
        <p className="lead">
          Navigate through {curriculum.tracks.length} tracks and {totalModules} modules.
          Complete modules to unlock the next tier and progress through foundation, practice,
          core and advanced phases.
        </p>
        <Legend />
      </section>

      <TrackTreeSection
        tracks={curriculum.tracks}
        activeTrack={activeTrack}
        activeModule={activeModule}
      />
    </main>
  );
}
