"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";

import { AppShell } from "@/app/components/AppShell";
import { useAuth } from "@/app/components/AuthProvider";
import { SidebarSlotProvider } from "@/app/components/SidebarSlotProvider";

const PUBLIC_PATHS = new Set(["/login"]);

export function AuthGuard({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  const currentPath = pathname ?? "/";
  const isPublicPath = PUBLIC_PATHS.has(currentPath);

  useEffect(() => {
    if (status === "unauthenticated" && !isPublicPath) {
      const currentSearch = typeof window === "undefined" ? "" : window.location.search;
      const nextTarget = `${currentPath}${currentSearch}`;
      router.replace(`/login?next=${encodeURIComponent(nextTarget)}`);
    }
  }, [currentPath, isPublicPath, router, status]);

  if (isPublicPath) {
    return children;
  }

  if (status === "authenticated") {
    return (
      <SidebarSlotProvider>
        <AppShell>{children}</AppShell>
      </SidebarSlotProvider>
    );
  }

  return (
    <main className="page-shell auth-gate-page">
      <section className="panel auth-gate-panel" aria-live="polite">
        <p className="eyebrow">Authentication</p>
        <h1>{status === "loading" ? "Checking your session..." : "Redirecting to login..."}</h1>
        <p className="lead">
          {status === "loading"
            ? "The frontend is validating the active session cookie with /auth/me before opening the workspace."
            : "This page requires an authenticated learner account."}
        </p>
      </section>
    </main>
  );
}
