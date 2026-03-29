"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import {
  clearStoredAuth,
  fetchCurrentSession,
  getStoredAccessToken,
  getStoredAuthSession,
  loginWithPassword,
  registerWithPassword,
  type AuthCredentials,
  type AuthSession,
} from "@/services/auth";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  status: AuthStatus;
  session: AuthSession | null;
  login: (payload: AuthCredentials) => Promise<AuthSession>;
  register: (payload: AuthCredentials) => Promise<AuthSession>;
  logout: () => void;
  refreshSession: () => Promise<AuthSession>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [session, setSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      const storedToken = getStoredAccessToken();
      const storedSession = getStoredAuthSession();

      if (!storedToken) {
        if (!cancelled) {
          setSession(storedSession);
          setStatus("unauthenticated");
        }
        return;
      }

      if (storedSession && !cancelled) {
        setSession(storedSession);
      }

      try {
        const nextSession = await fetchCurrentSession(storedToken);
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

  function logout() {
    clearStoredAuth();
    setSession(null);
    setStatus("unauthenticated");
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
