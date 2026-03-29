"use client";

type Props = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function GlobalError({ error, reset }: Props) {
  return (
    <html lang="en">
      <body>
        <main className="page-shell">
          <section className="panel auth-gate-panel" aria-live="assertive">
            <p className="eyebrow">Application error</p>
            <h1>The workspace could not bootstrap.</h1>
            <p className="lead">
              A required backend dependency failed during page rendering, so the app stopped instead of showing fake
              data.
            </p>
            <p className="muted">{error.message || "Unknown application error."}</p>
            <button type="button" className="action-btn" onClick={() => reset()}>
              Retry
            </button>
          </section>
        </main>
      </body>
    </html>
  );
}
