"use client";

import { useCallback, useEffect, useState } from "react";

type TmuxSession = {
  name: string;
  created_at: number;
  windows: number;
  attached: boolean;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchSessions(): Promise<TmuxSession[]> {
  const res = await fetch(`${API_URL}/api/v1/tmux`, { cache: "no-store" });
  if (!res.ok) return [];
  return (await res.json()) as TmuxSession[];
}

async function startSession(name: string): Promise<{ ok: boolean; detail?: string }> {
  const res = await fetch(`${API_URL}/api/v1/tmux/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    return { ok: false, detail: body.detail ?? `Error ${res.status}` };
  }
  return { ok: true };
}

async function attachSession(name: string): Promise<string | null> {
  const res = await fetch(`${API_URL}/api/v1/tmux/attach`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) return null;
  const body = (await res.json()) as { command: string };
  return body.command;
}

async function killSession(name: string): Promise<boolean> {
  const res = await fetch(`${API_URL}/api/v1/tmux/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
  return res.ok;
}

function formatCreated(epoch: number): string {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(epoch * 1000));
}

export default function SessionsClient() {
  const [sessions, setSessions] = useState<TmuxSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [attachCmd, setAttachCmd] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setSessions(await fetchSessions());
    setLoading(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchSessions().then((data) => {
      if (!cancelled) {
        setSessions(data);
        setLoading(false);
      }
    });
    return () => { cancelled = true; };
  }, []);

  async function handleStart() {
    const trimmed = newName.trim();
    if (!trimmed) return;
    setError(null);
    const result = await startSession(trimmed);
    if (!result.ok) {
      setError(result.detail ?? "Failed to start session");
      return;
    }
    setNewName("");
    await refresh();
  }

  async function handleAttach(name: string) {
    setAttachCmd(null);
    const cmd = await attachSession(name);
    if (cmd) setAttachCmd(cmd);
  }

  async function handleKill(name: string) {
    await killSession(name);
    setAttachCmd(null);
    await refresh();
  }

  return (
    <section className="sessions-content">
      <div className="panel sessions-create">
        <h2>Start a new session</h2>
        <div className="sessions-form">
          <label htmlFor="session-name" className="sr-only">Session name</label>
          <input
            id="session-name"
            className="sessions-input"
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Session name (e.g. shell-practice)"
            pattern="^[a-zA-Z0-9_-]+$"
            maxLength={64}
            onKeyDown={(e) => { if (e.key === "Enter") handleStart(); }}
          />
          <button type="button" className="btn btn--primary" onClick={handleStart} disabled={!newName.trim()}>
            Start
          </button>
        </div>
        {error && <p className="sessions-error" role="alert">{error}</p>}
      </div>

      {attachCmd && (
        <div className="panel sessions-attach-hint">
          <p>Run this in your terminal to attach:</p>
          <code className="sessions-cmd">{attachCmd}</code>
        </div>
      )}

      <div className="panel sessions-list" aria-live="polite">
        <h2>Active sessions</h2>
        {loading && <p className="muted">Loading...</p>}
        {!loading && sessions.length === 0 && (
          <p className="muted">No active sessions. Start one above.</p>
        )}
        {!loading && sessions.length > 0 && (
          <table className="sessions-table">
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Created</th>
                <th scope="col">Windows</th>
                <th scope="col">Attached</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.name}>
                  <td className="sessions-name">{s.name}</td>
                  <td>{formatCreated(s.created_at)}</td>
                  <td>{s.windows}</td>
                  <td>{s.attached ? "yes" : "no"}</td>
                  <td className="sessions-actions">
                    <button type="button" className="btn btn--small" onClick={() => handleAttach(s.name)} aria-label={`Attach to ${s.name}`}>
                      Attach
                    </button>
                    <button type="button" className="btn btn--small btn--danger" onClick={() => handleKill(s.name)} aria-label={`Kill session ${s.name}`}>
                      Kill
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
}
