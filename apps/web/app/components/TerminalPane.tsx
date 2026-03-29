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

export function TerminalPane({ session }: { session: string }) {
  const [data, setData] = useState<PaneData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const preRef = useRef<HTMLPreElement>(null);

  const fetchPane = useCallback(async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    try {
      const resp = await fetch(`${apiUrl}/api/v1/tmux/pane/${encodeURIComponent(session)}`);
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({ detail: `HTTP ${resp.status}` }));
        setError(body.detail ?? `HTTP ${resp.status}`);
        return;
      }
      const payload = (await resp.json()) as PaneData;
      setData(payload);
      setError(null);
    } catch {
      setError("Cannot reach API");
    }
  }, [session]);

  useEffect(() => {
    if (paused) return;

    fetchPane();
    const id = setInterval(fetchPane, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [fetchPane, paused]);

  // Auto-scroll to bottom on new content
  useEffect(() => {
    if (preRef.current) {
      preRef.current.scrollTop = preRef.current.scrollHeight;
    }
  }, [data?.content]);

  return (
    <article className="panel terminal-pane">
      <div className="terminal-pane-header">
        <p className="eyebrow">Live Terminal</p>
        <div className="terminal-pane-controls">
          <span className="terminal-pane-session">{session}</span>
          <button
            className="terminal-pane-toggle"
            onClick={() => setPaused((p) => !p)}
            title={paused ? "Resume polling" : "Pause polling"}
          >
            {paused ? "Resume" : "Pause"}
          </button>
        </div>
      </div>

      {error ? (
        <div className="terminal-pane-error">{error}</div>
      ) : (
        <pre
          ref={preRef}
          className="terminal-pane-content"
          style={{
            minHeight: data ? `${Math.min(data.rows, 24) * 1.3}em` : "12em",
          }}
        >
          {data?.content ?? "Connecting..."}
        </pre>
      )}
    </article>
  );
}
