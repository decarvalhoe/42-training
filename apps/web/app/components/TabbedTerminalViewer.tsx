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
  const [lastActivity, setLastActivity] = useState<Record<TabName, number>>({
    work: 0,
    build: 0,
    tests: 0,
  });
  const [paused, setPaused] = useState(false);
  const preRef = useRef<HTMLPreElement>(null);

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
    if (preRef.current) {
      preRef.current.scrollTop = preRef.current.scrollHeight;
    }
  }, [panes, activeTab]);

  const mostRecentTab = TABS.reduce((a, b) => (lastActivity[a] >= lastActivity[b] ? a : b));

  const activeData = panes[activeTab];
  const activeError = errors[activeTab];

  return (
    <article className="panel terminal-viewer">
      <div className="terminal-viewer-tabs">
        {TABS.map((tab) => (
          <button
            key={tab}
            className={`terminal-viewer-tab${tab === activeTab ? " terminal-viewer-tab--active" : ""}${tab === mostRecentTab && lastActivity[tab] > 0 ? " terminal-viewer-tab--recent" : ""}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab}
          </button>
        ))}
        <div className="terminal-viewer-spacer" />
        <span className="terminal-pane-session">
          {sessionPrefix}:{activeTab}
        </span>
        <button
          className="terminal-pane-toggle"
          onClick={() => setPaused((p) => !p)}
          title={paused ? "Resume polling" : "Pause polling"}
        >
          {paused ? "Resume" : "Pause"}
        </button>
      </div>

      {activeError ? (
        <div className="terminal-pane-error">{activeError}</div>
      ) : (
        <pre
          ref={preRef}
          className="terminal-pane-content"
          style={{
            minHeight: activeData ? `${Math.min(activeData.rows, 24) * 1.3}em` : "12em",
          }}
        >
          {activeData?.content ?? "Connecting..."}
        </pre>
      )}
    </article>
  );
}
