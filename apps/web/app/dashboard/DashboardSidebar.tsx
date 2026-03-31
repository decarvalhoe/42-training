"use client";

/**
 * Client wrapper to inject dashboard stats into the AppShell sidebar.
 * Issue #288 — merge dual sidebars.
 */

import { SidebarContent } from "@/app/components/SidebarSlotProvider";

type Props = {
  completedModules: number;
  totalModules: number;
  completionEvents: number;
  successRate: number;
  defensesStarted: number;
  mentorQueries: number;
  totalSkills: number;
  trackCount: number;
  activePanes: number;
  idlePanes: number;
  currentExercise: string | null;
  currentStep: string | null;
};

function StatLine({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-3 py-2">
      <div className="flex items-baseline justify-between">
        <span className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">{label}</span>
        <span className="font-mono text-sm font-bold text-[var(--shell-ink)]">{value}</span>
      </div>
      <p className="mt-1 font-mono text-[8px] leading-4 text-[var(--shell-muted)]">{detail}</p>
    </div>
  );
}

export function DashboardSidebar(props: Props) {
  return (
    <SidebarContent>
      <div className="flex flex-col gap-4">
        <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Stats</p>
        <div className="grid gap-2">
          <StatLine label="Modules" value={`${props.completedModules}/${props.totalModules}`} detail={`${props.completionEvents} completions`} />
          <StatLine label="Success" value={`${props.successRate}%`} detail="checkpoint reliability" />
          <StatLine label="Defense" value={`${props.defensesStarted}`} detail="sessions started" />
          <StatLine label="Mentor" value={`${props.mentorQueries}`} detail="AI interactions" />
          <StatLine label="Skills" value={`${props.totalSkills}`} detail={`${props.trackCount} tracks`} />
        </div>

        <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Session health</p>
        <div className="grid gap-2">
          <div className="flex items-center justify-between border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-3 py-2 font-mono text-[10px] uppercase tracking-[0.24em]">
            <span className="text-[var(--shell-muted)]">Live</span>
            <span className="text-[var(--shell-success)]">{props.activePanes}</span>
          </div>
          <div className="flex items-center justify-between border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-3 py-2 font-mono text-[10px] uppercase tracking-[0.24em]">
            <span className="text-[var(--shell-muted)]">Idle</span>
            <span className="text-[var(--shell-ink)]">{props.idlePanes}</span>
          </div>
          <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-3 py-2">
            <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Focus</p>
            <p className="mt-1 font-mono text-[10px] text-[var(--shell-ink)]">
              {props.currentExercise ?? "No active exercise"}
            </p>
          </div>
        </div>
      </div>
    </SidebarContent>
  );
}
