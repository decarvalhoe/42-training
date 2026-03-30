"use client";

type Props = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function ErrorPage({ error, reset }: Props) {
  return (
    <main className="page-shell">
      <section className="panel auth-gate-panel" aria-live="assertive">
        <p className="eyebrow">Backend unavailable</p>
        <h1>The application could not load live data.</h1>
        <p className="lead">
          The frontend stopped instead of switching silently to fabricated fallback data.
        </p>
        <p className="muted">{error.message || "Unknown application error."}</p>
        <button type="button" className="action-btn" onClick={() => reset()}>
          Retry
        </button>
      </section>
    </main>
  );
}
