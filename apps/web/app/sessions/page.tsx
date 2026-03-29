import Link from "next/link";

export const metadata = {
  title: "Sessions — 42 Training",
  description: "Manage tmux shell practice sessions",
};

export default function SessionsPage() {
  return (
    <main className="page-shell sessions-page">
      <nav className="breadcrumb">
        <Link href="/">Dashboard</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Sessions</span>
      </nav>

      <section className="sessions-hero panel">
        <p className="eyebrow">Sessions</p>
        <h1>Manage your shell practice sessions from here.</h1>
        <p className="lead">
          Start, inspect or tear down tmux sessions used for hands-on shell
          exercises. Each session is an isolated terminal you can reconnect to
          at any time.
        </p>
      </section>

      <SessionsClient />
    </main>
  );
}

import SessionsClient from "./SessionsClient";
