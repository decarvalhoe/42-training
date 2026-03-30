"use client";

import { useEffect, useRef, useState } from "react";

type BootLine = {
  text: string;
  style?: "ok" | "info" | "warn" | "dim" | "bold";
  delay: number;
};

const BOOT_LINES: BootLine[] = [
  { text: "42-training v0.1.0 — agent workspace bootstrap", style: "bold", delay: 0 },
  { text: "", delay: 200 },
  { text: "[kernel]  loading curriculum engine...", style: "dim", delay: 400 },
  { text: "[kernel]  source policy: official_42 > community > tooling", style: "dim", delay: 700 },
  { text: "[kernel]  tracks: shell, c, python_ai", style: "dim", delay: 950 },
  { text: "", delay: 1100 },
  { text: "starting tmux agent sessions", style: "info", delay: 1300 },
  { text: "", delay: 1450 },
  { text: "  tmux new-session -d -s mentor", style: "dim", delay: 1600 },
  { text: "  [mentor]       pedagogical guidance       ....  OK", style: "ok", delay: 2000 },
  { text: "  tmux new-session -d -s librarian", style: "dim", delay: 2300 },
  { text: "  [librarian]    resource retrieval          ....  OK", style: "ok", delay: 2700 },
  { text: "  tmux new-session -d -s reviewer", style: "dim", delay: 2950 },
  { text: "  [reviewer]     code review                ....  OK", style: "ok", delay: 3350 },
  { text: "  tmux new-session -d -s examiner", style: "dim", delay: 3600 },
  { text: "  [examiner]     defense sessions           ....  OK", style: "ok", delay: 4000 },
  { text: "  tmux new-session -d -s orchestrator", style: "dim", delay: 4250 },
  { text: "  [orchestrator] agent coordination         ....  OK", style: "ok", delay: 4650 },
  { text: "", delay: 4850 },
  { text: "[redis]   conversation memory .............. ready", style: "info", delay: 5050 },
  { text: "[api]     progression engine ............... ready", style: "info", delay: 5300 },
  { text: "[gateway] ai orchestration ................. ready", style: "info", delay: 5550 },
  { text: "", delay: 5700 },
  { text: "all 5 agent sessions active", style: "ok", delay: 5900 },
  { text: "awaiting learner authentication...", style: "warn", delay: 6200 },
];

export function BootSequence() {
  const [visibleCount, setVisibleCount] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = [];

    for (let i = 0; i < BOOT_LINES.length; i++) {
      timers.push(
        setTimeout(() => {
          setVisibleCount(i + 1);
        }, BOOT_LINES[i].delay),
      );
    }

    return () => timers.forEach(clearTimeout);
  }, []);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [visibleCount]);

  return (
    <div className="boot-sequence" ref={containerRef}>
      <div className="boot-sequence-inner">
        {BOOT_LINES.slice(0, visibleCount).map((line, i) => (
          <div
            key={i}
            className={`boot-line ${line.style ? `boot-line--${line.style}` : ""}`}
          >
            {line.text || "\u00A0"}
          </div>
        ))}
        {visibleCount < BOOT_LINES.length && (
          <span className="boot-cursor" />
        )}
      </div>
    </div>
  );
}
