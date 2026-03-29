"use client";

import { useRouter } from "next/navigation";

import { useAuth } from "@/app/components/AuthProvider";

export function AuthStatus() {
  const router = useRouter();
  const { logout, session, status } = useAuth();

  if (status === "loading") {
    return <span className="nav-auth-loading">Checking session...</span>;
  }

  if (status !== "authenticated" || session === null) {
    return null;
  }

  function handleLogout() {
    logout();
    router.replace("/login");
    router.refresh();
  }

  return (
    <div className="nav-auth">
      <div className="nav-auth-copy">
        <strong>{session.user.email}</strong>
        <span>{session.learnerProfile ? `${session.learnerProfile.track} profile` : "No active profile"}</span>
      </div>
      <button type="button" className="nav-auth-btn" onClick={handleLogout}>
        Logout
      </button>
    </div>
  );
}
