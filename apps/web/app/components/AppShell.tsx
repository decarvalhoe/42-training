"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

import { useAuth } from "@/app/components/AuthProvider";
import { useUiPreferences } from "@/app/components/UiPreferencesProvider";

type NavItem = {
  href: string;
  label: string;
  shortLabel: string;
  isActive: (pathname: string) => boolean;
};

type RailAction = {
  href: string;
  label: string;
  shortLabel: string;
  variant: "primary" | "secondary";
};

const DESKTOP_BREAKPOINT = 1280;
const TABLET_BREAKPOINT = 768;
const DESKTOP_EXPANDED_WIDTH = 240;
const DESKTOP_COLLAPSED_WIDTH = 48;
const MOBILE_COLLAPSED_WIDTH = 40;
const SIDEBAR_STORAGE_KEY = "app-shell.desktop-expanded";

const PRIMARY_NAV: NavItem[] = [
  {
    href: "/dashboard",
    label: "Dashboard",
    shortLabel: "DB",
    isActive: (pathname) => pathname === "/" || pathname.startsWith("/dashboard"),
  },
  {
    href: "/tracks",
    label: "Tracks",
    shortLabel: "TR",
    isActive: (pathname) => pathname.startsWith("/tracks"),
  },
  {
    href: "/modules",
    label: "Modules",
    shortLabel: "MD",
    isActive: (pathname) => pathname.startsWith("/modules"),
  },
  {
    href: "/defense",
    label: "Defense",
    shortLabel: "DF",
    isActive: (pathname) => pathname.startsWith("/defense"),
  },
  {
    href: "/mentor",
    label: "Mentor",
    shortLabel: "MN",
    isActive: (pathname) => pathname.startsWith("/mentor"),
  },
];

const UTILITY_NAV: NavItem[] = [
  {
    href: "/progression",
    label: "Progression",
    shortLabel: "PG",
    isActive: (pathname) => pathname.startsWith("/progression"),
  },
  {
    href: "/review",
    label: "Review",
    shortLabel: "RV",
    isActive: (pathname) => pathname.startsWith("/review"),
  },
  {
    href: "/evidence",
    label: "Evidence",
    shortLabel: "EV",
    isActive: (pathname) => pathname.startsWith("/evidence"),
  },
  {
    href: "/profiles",
    label: "Profiles",
    shortLabel: "PF",
    isActive: (pathname) => pathname.startsWith("/profiles"),
  },
  {
    href: "/sessions",
    label: "Sessions",
    shortLabel: "SS",
    isActive: (pathname) => pathname.startsWith("/sessions"),
  },
  {
    href: "/analytics",
    label: "Analytics",
    shortLabel: "AN",
    isActive: (pathname) => pathname.startsWith("/analytics"),
  },
];

function getModuleContext(pathname: string) {
  const match = pathname.match(/^\/modules\/([^/?#]+)/);
  return match?.[1] ?? null;
}

function buildRouteLabel(pathname: string) {
  if (pathname === "/" || pathname.startsWith("/dashboard")) return "skill graph // learner state";
  if (pathname.startsWith("/tracks")) return "track explorer // curriculum";
  if (pathname.startsWith("/modules")) {
    const moduleId = getModuleContext(pathname);
    return `module learning // ${moduleId ?? "active module"}`;
  }
  if (pathname.startsWith("/defense")) return "defense session // oral evaluation";
  if (pathname.startsWith("/mentor")) return "ai mentor // guided questioning";
  if (pathname.startsWith("/review")) return "guided review // peer preparation";
  if (pathname.startsWith("/evidence")) return "evidence // linked artifacts";
  if (pathname.startsWith("/profiles")) return "profiles // learner scope";
  if (pathname.startsWith("/sessions")) return "sessions // tmux runtime";
  if (pathname.startsWith("/analytics")) return "analytics // pedagogical events";
  if (pathname.startsWith("/progression")) return "progression // next steps";
  return "42-training // workspace";
}

function getRailActions(pathname: string): RailAction[] {
  const moduleId = getModuleContext(pathname);
  const moduleQuery = moduleId === null ? "" : `?module=${encodeURIComponent(moduleId)}`;

  if (pathname.startsWith("/tracks")) {
    return [
      {
        href: "/modules",
        label: "START MODULE",
        shortLabel: "▶",
        variant: "primary",
      },
    ];
  }

  if (pathname.startsWith("/modules")) {
    return [
      {
        href: `/review${moduleQuery}`,
        label: "SUBMIT",
        shortLabel: "▶",
        variant: "primary",
      },
      {
        href: `/mentor${moduleQuery}`,
        label: "ASK MENTOR",
        shortLabel: "?",
        variant: "secondary",
      },
    ];
  }

  return [];
}

function getSessionLabel(email: string | null) {
  if (email === null) {
    return "learner@42";
  }

  return email.includes("@") ? email.split("@")[0] : email;
}

function navItemClass(isActive: boolean) {
  return isActive
    ? "text-[var(--shell-success)]"
    : "text-[var(--shell-muted)] transition-colors hover:text-[var(--shell-ink)]";
}

function railButtonClass(variant: RailAction["variant"], expanded: boolean) {
  const base =
    "flex items-center justify-center rounded-none border text-[10px] font-semibold tracking-[0.28em] transition-colors";
  const sizing = expanded ? "min-h-10 gap-2 px-3 py-2" : "h-10 w-full";

  if (variant === "primary") {
    return `${base} ${sizing} border-[var(--shell-success)] bg-[var(--shell-success)] text-[var(--shell-canvas)] hover:bg-[var(--shell-success-strong)]`;
  }

  return `${base} ${sizing} border-[var(--shell-border-strong)] bg-[var(--shell-panel)] text-[var(--shell-ink)] hover:border-[var(--shell-muted)] hover:text-[var(--shell-success)]`;
}

function SidebarLink({
  expanded,
  item,
  pathname,
}: {
  expanded: boolean;
  item: NavItem;
  pathname: string;
}) {
  const active = item.isActive(pathname);

  return (
    <Link
      href={item.href}
      className={[
        "flex items-center gap-3 border border-transparent px-3 py-2 text-[10px] font-medium uppercase tracking-[0.24em]",
        active
          ? "border-[var(--shell-border)] bg-[var(--shell-panel)] text-[var(--shell-success)]"
          : "text-[var(--shell-muted)] transition-colors hover:text-[var(--shell-ink)]",
      ].join(" ")}
      aria-current={active ? "page" : undefined}
    >
      <span className="inline-flex min-w-6 justify-center text-[11px] text-[var(--shell-success)]">
        {item.shortLabel}
      </span>
      {expanded ? <span>{item.label}</span> : null}
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  const router = useRouter();
  const { density } = useUiPreferences();
  const { logout, session, status } = useAuth();
  const [viewportWidth, setViewportWidth] = useState<number | null>(null);
  const [desktopExpanded, setDesktopExpanded] = useState(true);
  const [overlayExpanded, setOverlayExpanded] = useState(false);

  useEffect(() => {
    function syncViewport() {
      setViewportWidth(window.innerWidth);
    }

    syncViewport();
    window.addEventListener("resize", syncViewport);
    return () => window.removeEventListener("resize", syncViewport);
  }, []);

  useEffect(() => {
    if (viewportWidth === null) {
      return;
    }

    if (viewportWidth < DESKTOP_BREAKPOINT) {
      setOverlayExpanded(false);
      return;
    }

    const stored = window.localStorage.getItem(SIDEBAR_STORAGE_KEY);
    if (stored === null) {
      setDesktopExpanded(true);
      return;
    }

    setDesktopExpanded(stored === "true");
  }, [viewportWidth]);

  const isDesktop = viewportWidth !== null && viewportWidth >= DESKTOP_BREAKPOINT;
  const railWidth =
    viewportWidth !== null && viewportWidth < TABLET_BREAKPOINT
      ? MOBILE_COLLAPSED_WIDTH
      : DESKTOP_COLLAPSED_WIDTH;
  const isExpanded = isDesktop ? desktopExpanded : overlayExpanded;
  const sidebarWidth = isExpanded ? DESKTOP_EXPANDED_WIDTH : railWidth;
  const contentOffset = isDesktop && isExpanded ? DESKTOP_EXPANDED_WIDTH : railWidth;
  const railActions = getRailActions(pathname);
  const sessionLabel = getSessionLabel(session?.user.email ?? null);
  const trackLabel = session?.learnerProfile?.track ?? "shell";
  const routeLabel = buildRouteLabel(pathname);
  const contentPadding = density === "compact" ? "px-4 py-4 lg:px-6 lg:py-5" : "px-4 py-5 lg:px-6 lg:py-6";

  async function handleLogout() {
    await logout();
    router.replace("/login");
    router.refresh();
  }

  function handleToggleShell() {
    if (isDesktop) {
      const next = !desktopExpanded;
      setDesktopExpanded(next);
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(next));
      return;
    }

    setOverlayExpanded((value) => !value);
  }

  return (
    <div className="min-h-screen bg-[var(--shell-canvas)] text-[var(--shell-ink)]">
      {!isDesktop && isExpanded ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/45"
          aria-label="Close navigation overlay"
          onClick={() => setOverlayExpanded(false)}
        />
      ) : null}

      <aside
        className="fixed inset-y-0 left-0 z-40 overflow-hidden border-r border-[var(--shell-border)] bg-[var(--shell-sidebar)] transition-[width] duration-200"
        style={{ width: `${sidebarWidth}px` }}
      >
        <div className="flex h-full flex-col">
          <div className="border-b border-[var(--shell-border)] px-2 py-3">
            <div className="flex items-center justify-between gap-2">
              {isExpanded ? (
                <div className="min-w-0">
                  <p className="font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--shell-success)]">
                    42:training
                  </p>
                  <p className="mt-1 truncate font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
                    {routeLabel}
                  </p>
                </div>
              ) : (
                <span className="inline-flex w-full justify-center font-mono text-[11px] font-semibold uppercase tracking-[0.22em] text-[var(--shell-success)]">
                  42
                </span>
              )}

              <button
                type="button"
                className="inline-flex h-8 items-center justify-center border border-[var(--shell-border-strong)] bg-[var(--shell-panel)] px-2 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-ink)] transition-colors hover:border-[var(--shell-success)] hover:text-[var(--shell-success)]"
                aria-label={isExpanded ? "Collapse sidebar" : "Expand sidebar"}
                onClick={handleToggleShell}
              >
                {isExpanded ? "◂ COLLAPSE" : "▸"}
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-2 py-3">
            <div className="space-y-5">
              <section className="space-y-2">
                {isExpanded ? (
                  <p className="px-1 font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">
                    Primary
                  </p>
                ) : null}
                <nav className="grid gap-1" aria-label="Primary workspace navigation">
                  {PRIMARY_NAV.map((item) => (
                    <SidebarLink key={item.href} expanded={isExpanded} item={item} pathname={pathname} />
                  ))}
                </nav>
              </section>

              <section className="space-y-2">
                {isExpanded ? (
                  <p className="px-1 font-mono text-[9px] uppercase tracking-[0.28em] text-[var(--shell-dim)]">
                    Workspace
                  </p>
                ) : null}
                <nav className="grid gap-1" aria-label="Secondary workspace navigation">
                  {UTILITY_NAV.map((item) => (
                    <SidebarLink key={item.href} expanded={isExpanded} item={item} pathname={pathname} />
                  ))}
                </nav>
              </section>
            </div>
          </div>

          <div className="mt-auto border-t border-[var(--shell-border)] px-2 py-3">
            <div className="flex flex-col gap-2">
              {railActions.map((action) => (
                <Link
                  key={`${action.href}-${action.label}`}
                  href={action.href}
                  className={railButtonClass(action.variant, isExpanded)}
                >
                  <span>{action.shortLabel}</span>
                  {isExpanded ? <span>{action.label}</span> : null}
                </Link>
              ))}

              <div
                className={[
                  "flex items-center border border-[var(--shell-border-strong)] bg-[var(--shell-panel)] text-[var(--shell-muted)]",
                  isExpanded ? "min-h-10 gap-2 px-3 py-2" : "h-10 w-full justify-center",
                ].join(" ")}
                aria-label="Terminal status live"
              >
                <span className="text-[13px] text-[var(--shell-success)]">⬤</span>
                {isExpanded ? (
                  <span className="font-mono text-[10px] uppercase tracking-[0.24em]">
                    terminal live
                  </span>
                ) : null}
              </div>
            </div>
          </div>
        </div>
      </aside>

      <div
        className="min-h-screen transition-[margin-left] duration-200"
        style={{ marginLeft: `${contentOffset}px` }}
      >
        <header className="sticky top-0 z-20 border-b border-[var(--shell-border)] bg-[var(--shell-panel)]/95 backdrop-blur">
          <div className="flex min-h-12 items-center gap-4 px-4 py-3 lg:px-6">
            <div className="min-w-0">
              <p className="font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--shell-success)]">
                {routeLabel}
              </p>
            </div>

            <nav className="flex min-w-0 flex-1 items-center gap-4 overflow-x-auto font-mono text-[10px] uppercase tracking-[0.24em]">
              {PRIMARY_NAV.map((item) => {
                const active = item.isActive(pathname);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={navItemClass(active)}
                    aria-current={active ? "page" : undefined}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <div className="ml-auto flex items-center gap-3 whitespace-nowrap font-mono text-[10px] uppercase tracking-[0.22em] text-[var(--shell-muted)]">
              {status === "authenticated" && session !== null ? (
                <>
                  <span>{sessionLabel}</span>
                  <span>//</span>
                  <span>{trackLabel} track</span>
                  <span className="text-[var(--shell-success)]">●</span>
                  <button
                    type="button"
                    className="border border-[var(--shell-border-strong)] px-2 py-1 text-[var(--shell-ink)] transition-colors hover:border-[var(--shell-success)] hover:text-[var(--shell-success)]"
                    onClick={() => void handleLogout()}
                  >
                    Logout
                  </button>
                </>
              ) : (
                <span>checking session</span>
              )}
            </div>
          </div>
        </header>

        <main id="main-content" className={`relative ${contentPadding}`}>
          {children}
        </main>
      </div>
    </div>
  );
}
