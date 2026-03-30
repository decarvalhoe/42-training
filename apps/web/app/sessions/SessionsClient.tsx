"use client";

import { useCallback, useEffect, useState } from "react";

import {
  GuidedActionButton,
  GuidedBadge,
  GuidedEmptyState,
  GuidedField,
  GuidedInput,
  GuidedPanel,
  GuidedSidebarSection,
} from "@/app/components/GuidedSurface";

type TmuxSession = {
  name: string;
  created_at: number;
  windows: number;
  attached: boolean;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchSessions(): Promise<TmuxSession[]> {
  const response = await fetch(`${API_URL}/api/v1/tmux`, { cache: "no-store" });
  if (!response.ok) {
    return [];
  }
  return (await response.json()) as TmuxSession[];
}

async function startSession(name: string): Promise<{ ok: boolean; detail?: string }> {
  const response = await fetch(`${API_URL}/api/v1/tmux/start`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    return { ok: false, detail: body.detail ?? `Error ${response.status}` };
  }
  return { ok: true };
}

async function attachSession(name: string): Promise<string | null> {
  const response = await fetch(`${API_URL}/api/v1/tmux/attach`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!response.ok) {
    return null;
  }
  const body = (await response.json()) as { command: string };
  return body.command;
}

async function killSession(name: string): Promise<boolean> {
  const response = await fetch(`${API_URL}/api/v1/tmux/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
  return response.ok;
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
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleStart() {
    const trimmed = newName.trim();
    if (!trimmed) {
      return;
    }

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
    const command = await attachSession(name);
    if (command) {
      setAttachCmd(command);
    }
  }

  async function handleKill(name: string) {
    await killSession(name);
    setAttachCmd(null);
    await refresh();
  }

  if (loading && sessions.length === 0) {
    return <GuidedEmptyState title="Loading tmux runtime..." body="The shell practice runtime is syncing active terminal sessions." />;
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
      <div className="grid gap-4">
        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Sessions">
            <h1 className="font-mono text-2xl font-semibold uppercase tracking-[0.08em] text-[var(--shell-ink)]">
              Tmux runtime
            </h1>
            <p className="text-sm leading-7 text-[var(--shell-muted)]">
              Start, attach and recycle the isolated shell workspaces used by guided modules, mentor context and defense sessions.
            </p>
          </GuidedSidebarSection>
        </GuidedPanel>

        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Create">
            <GuidedField label="Session name">
              <GuidedInput
                value={newName}
                onChange={(event) => setNewName(event.target.value)}
                placeholder="shell-practice"
                pattern="^[a-zA-Z0-9_-]+$"
                maxLength={64}
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    void handleStart();
                  }
                }}
              />
            </GuidedField>
            <GuidedActionButton onClick={() => void handleStart()} disabled={!newName.trim()}>
              Start session
            </GuidedActionButton>
            {error ? (
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-danger)]" role="alert">
                {error}
              </p>
            ) : null}
          </GuidedSidebarSection>
        </GuidedPanel>

        <GuidedPanel className="px-5 py-5">
          <GuidedSidebarSection label="Runtime stats">
            <div className="grid gap-3">
              <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
                <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Active sessions</p>
                <p className="mt-3 font-mono text-xl font-semibold text-[var(--shell-ink)]">{sessions.length}</p>
              </div>
              <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
                <p className="font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">Attached</p>
                <p className="mt-3 font-mono text-xl font-semibold text-[var(--shell-ink)]">
                  {sessions.filter((session) => session.attached).length}
                </p>
              </div>
            </div>
          </GuidedSidebarSection>
        </GuidedPanel>
      </div>

      <div className="grid gap-4">
        {attachCmd ? (
          <GuidedPanel className="px-5 py-5">
            <GuidedSidebarSection label="Attach command">
              <pre className="overflow-x-auto border border-[var(--shell-border)] bg-[var(--shell-sidebar)] px-4 py-4 font-mono text-[12px] leading-6 text-[var(--shell-success)]">
                {attachCmd}
              </pre>
            </GuidedSidebarSection>
          </GuidedPanel>
        ) : null}

        <GuidedPanel className="px-6 py-6">
          <p className="font-mono text-[10px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
            sessions // tmux runtime
          </p>
          <h2 className="mt-4 font-mono text-2xl font-semibold uppercase tracking-[0.08em] text-[var(--shell-ink)]">
            Active terminal sessions
          </h2>

          {sessions.length === 0 ? (
            <div className="mt-6 border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-5 py-5">
              <p className="text-sm leading-7 text-[var(--shell-muted)]">
                No active sessions. Start one from the rail to create the first workspace.
              </p>
            </div>
          ) : (
            <div className="mt-6 grid gap-4">
              {sessions.map((session) => (
                <article key={session.name} className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-5 py-5">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <h3 className="font-mono text-sm font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                        {session.name}
                      </h3>
                      <p className="mt-2 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-dim)]">
                        created {formatCreated(session.created_at)}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <GuidedBadge>{session.windows} windows</GuidedBadge>
                      <GuidedBadge tone={session.attached ? "success" : "default"}>
                        {session.attached ? "attached" : "detached"}
                      </GuidedBadge>
                    </div>
                  </div>

                  <div className="mt-5 flex flex-wrap gap-3">
                    <GuidedActionButton variant="secondary" onClick={() => void handleAttach(session.name)}>
                      Attach
                    </GuidedActionButton>
                    <GuidedActionButton variant="danger" onClick={() => void handleKill(session.name)}>
                      Kill
                    </GuidedActionButton>
                  </div>
                </article>
              ))}
            </div>
          )}
        </GuidedPanel>
      </div>
    </div>
  );
}
