import type { TmuxSession } from "@/lib/api";

function StatusDot({ status }: { status: TmuxSession["status"] }) {
  return (
    <span
      className={`status-dot${status === "active" ? " status-dot--active" : ""}`}
      role="img"
      aria-label={`Status: ${status}`}
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
