import Link from "next/link";

import { getDashboardData } from "@/lib/api";

const NAV_LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/progression", label: "Progression" },
] as const;

export async function NavHeader() {
  const data = await getDashboardData();
  const activeTrack = data.progression.learning_plan?.active_course ?? "shell";

  return (
    <header className="nav-header">
      <div className="nav-brand">
        <Link href="/" className="nav-logo">42-training</Link>
        <span className="nav-track-indicator">{activeTrack}</span>
      </div>
      <nav className="nav-links">
        {NAV_LINKS.map((link) => (
          <Link key={link.href} href={link.href} className="nav-link">
            {link.label}
          </Link>
        ))}
        {data.curriculum.tracks.map((track) => (
          <Link
            key={track.id}
            href={`/tracks/${track.id}`}
            className={`nav-link ${track.id === activeTrack ? "nav-link--active" : ""}`}
          >
            {track.title}
          </Link>
        ))}
      </nav>
    </header>
  );
}
