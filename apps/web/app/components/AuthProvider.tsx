"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import {
  clearStoredAuth,
  fetchCurrentSession,
  getStoredAuthSession,
  loginWithPassword,
  logoutCurrentSession,
  registerWithPassword,
  type AuthCredentials,
  type AuthSession,
} from "@/services/auth";

const VISUAL_TEST_SESSION_ENABLED = process.env.NEXT_PUBLIC_ENABLE_VISUAL_TEST_SESSION === "true";
const VISUAL_TEST_SESSION_COOKIE = "training_visual_session";
const VISUAL_TEST_SESSION: AuthSession = {
  user: {
    id: "visual-user",
    email: "visual@42-training.local",
    status: "active",
  },
  learnerProfile: {
    id: "visual-profile",
    login: "visual-shell",
    track: "shell",
    current_module: "shell-basics",
  },
  profiles: [
    {
      id: "visual-profile",
      login: "visual-shell",
      track: "shell",
      current_module: "shell-basics",
    },
  ],
};

function getWindowVisualSession() {
  if (typeof window === "undefined") {
    return null;
  }

  const runtimeWindow = window as Window & {
    __TRAINING_VISUAL_AUTH__?: AuthSession;
  };

  return runtimeWindow.__TRAINING_VISUAL_AUTH__ ?? null;
}

function hasVisualTestSessionCookie() {
  if (typeof document === "undefined") {
    return false;
  }

  return document.cookie
    .split(";")
    .some((entry) => entry.trim() === `${VISUAL_TEST_SESSION_COOKIE}=1`);
}

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  status: AuthStatus;
  session: AuthSession | null;
  login: (payload: AuthCredentials) => Promise<AuthSession>;
  register: (payload: AuthCredentials) => Promise<AuthSession>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<AuthSession>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [session, setSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const storedSession = getStoredAuthSession();
      const windowVisualSession = getWindowVisualSession();
      const canUseVisualSession = VISUAL_TEST_SESSION_ENABLED || hasVisualTestSessionCookie();

      if ((windowVisualSession || canUseVisualSession) && !cancelled) {
        setSession(windowVisualSession ?? storedSession ?? VISUAL_TEST_SESSION);
        setStatus("authenticated");
        return;
      }

      if (storedSession && !cancelled) {
        setSession(storedSession);
      }

      try {
        const nextSession = await fetchCurrentSession();
        if (!cancelled) {
          setSession(nextSession);
          setStatus("authenticated");
        }
      } catch {
        clearStoredAuth();
        if (!cancelled) {
          setSession(null);
          setStatus("unauthenticated");
        }
      }
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, []);

  async function login(payload: AuthCredentials) {
    const nextSession = await loginWithPassword(payload);
    setSession(nextSession);
    setStatus("authenticated");
    return nextSession;
  }

  async function register(payload: AuthCredentials) {
    const nextSession = await registerWithPassword(payload);
    setSession(nextSession);
    setStatus("authenticated");
    return nextSession;
  }

  async function refreshSession() {
    const nextSession = await fetchCurrentSession();
    setSession(nextSession);
    setStatus("authenticated");
    return nextSession;
  }

  async function logout() {
    try {
      await logoutCurrentSession();
    } finally {
      clearStoredAuth();
      setSession(null);
      setStatus("unauthenticated");
    }
  }

  return (
    <AuthContext.Provider
      value={{
        status,
        session,
        login,
        register,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used inside AuthProvider");
  }

  return context;
}
