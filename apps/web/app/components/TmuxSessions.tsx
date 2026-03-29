import type { TmuxSession } from "@/lib/api";

function StatusDot({ status }: { status: TmuxSession["status"] }) {
  const color = status === "active" ? "var(--python)" : "var(--muted)";
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        backgroundColor: color,
        marginRight: 6,
      }}
    />
  );
}

export function TmuxSessions({ sessions }: { sessions: TmuxSession[] }) {
  if (sessions.length === 0) {
    return (
      <p className="muted">No tmux sessions detected.</p>
    );
  }

  return (
    <div className="tmux-list">
      {sessions.map((s) => (
        <div key={s.name} className="tmux-item">
          <div className="tmux-header">
            <strong>
              <StatusDot status={s.status} />
              {s.name}
            </strong>
            <span>{s.status}{s.attached ? " (attached)" : ""}</span>
          </div>
          <p className="muted">
            {s.windows} window{s.windows !== 1 ? "s" : ""} — last activity{" "}
            {new Date(s.last_activity).toLocaleString()}
          </p>
        </div>
      ))}
    </div>
  );
}
