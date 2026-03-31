"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type PaneData = {
  session: string;
  content: string;
  rows: number;
  cols: number;
  timestamp: string;
};

const POLL_INTERVAL_MS = 2000;
const TABS = ["work", "build", "tests"] as const;
type TabName = (typeof TABS)[number];

export function TabbedTerminalViewer({ sessionPrefix }: { sessionPrefix: string }) {
  const [activeTab, setActiveTab] = useState<TabName>("work");
  const [panes, setPanes] = useState<Record<TabName, PaneData | null>>({
    work: null,
    build: null,
    tests: null,
  });
  const [errors, setErrors] = useState<Record<TabName, string | null>>({
    work: null,
    build: null,
    tests: null,
  });
  const [, setLastActivity] = useState<Record<TabName, number>>({
    work: 0,
    build: 0,
    tests: 0,
  });
  const [paused, setPaused] = useState(false);
  const codeRef = useRef<HTMLDivElement>(null);

  const fetchPane = useCallback(
    async (tab: TabName) => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const session = `${sessionPrefix}:${tab}`;
      try {
        const resp = await fetch(`${apiUrl}/api/v1/tmux/pane/${encodeURIComponent(session)}`);
        if (!resp.ok) {
          const body = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
          setErrors((prev) => ({ ...prev, [tab]: body.detail ?? `HTTP ${resp.status}` }));
          return;
        }
        const payload = (await resp.json()) as PaneData;
        setPanes((prev) => {
          const oldContent = prev[tab]?.content;
          if (oldContent !== payload.content) {
            setLastActivity((la) => ({ ...la, [tab]: Date.now() }));
          }
          return { ...prev, [tab]: payload };
        });
        setErrors((prev) => ({ ...prev, [tab]: null }));
      } catch {
        setErrors((prev) => ({ ...prev, [tab]: "Cannot reach API" }));
      }
    },
    [sessionPrefix],
  );

  useEffect(() => {
    if (paused) return;

    const fetchAll = () => TABS.forEach((tab) => fetchPane(tab));
    fetchAll();
    const id = setInterval(fetchAll, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchPane, paused]);

  useEffect(() => {
    if (codeRef.current) {
      codeRef.current.scrollTop = codeRef.current.scrollHeight;
    }
  }, [panes, activeTab]);

  const activeData = panes[activeTab];
  const activeError = errors[activeTab];
  const lines = (activeData?.content ?? "Connecting...").split("\n");

  return (
    <div>
      {/* Tmux-style tabs (Figma 04 — learn42:work | build | tests) */}
      <div className="module-terminal-tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            className={`module-terminal-tab${tab === activeTab ? " module-terminal-tab--active" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {sessionPrefix}:{tab}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        <button
          className="module-terminal-tab"
          onClick={() => setPaused((p) => !p)}
          title={paused ? "Resume polling" : "Pause polling"}
        >
          {paused ? "▶ resume" : "⏸ pause"}
        </button>
      </div>

      {/* Code area with line numbers */}
      {activeError ? (
        <div className="module-terminal-code" style={{ color: "var(--shell-danger)", padding: "16px 24px" }}>
          {activeError}
        </div>
      ) : (
        <div className="module-terminal-code" ref={codeRef}>
          <div className="module-terminal-gutter">
            {lines.map((_, i) => (
              <span key={i}>{String(i + 1).padStart(2, "\u00A0")}</span>
            ))}
          </div>
          <div className="module-terminal-separator" />
          <div className="module-terminal-lines">
            {lines.map((line, i) => (
              <div key={i}>{line || "\u00A0"}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
