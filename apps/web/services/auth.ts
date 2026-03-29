export type AuthCredentials = {
  email: string;
  password: string;
};

export type AuthUser = {
  id: string;
  email: string;
  status: string;
};

export type AuthProfile = {
  id: string;
  login: string;
  track: string;
  current_module: string | null;
};

type AuthSessionResponse = {
  user: AuthUser;
  learner_profile: AuthProfile | null;
  profiles: AuthProfile[];
};

export type AuthSession = {
  user: AuthUser;
  learnerProfile: AuthProfile | null;
  profiles: AuthProfile[];
};

export const AUTH_SESSION_STORAGE_KEY = "training-auth-session";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class AuthApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "AuthApiError";
    this.status = status;
  }
}

function normalizeCredentials(payload: AuthCredentials): AuthCredentials {
  return {
    email: payload.email.trim().toLowerCase(),
    password: payload.password,
  };
}

function buildSession(data: AuthSessionResponse): AuthSession {
  return {
    user: data.user,
    learnerProfile: data.learner_profile ?? null,
    profiles: data.profiles,
  };
}

function serializeSession(session: AuthSession) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(session));
}

function persistSession(session: AuthSession): AuthSession {
  serializeSession(session);
  return session;
}

function extractErrorMessage(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string") {
    return payload.detail;
  }

  return fallback;
}

async function authRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });

  const payload = (response.status === 204 ? null : await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    throw new AuthApiError(
      extractErrorMessage(payload, `Authentication failed with status ${response.status}.`),
      response.status,
    );
  }

  return payload as T;
}

export function getStoredAuthSession(): AuthSession | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem(AUTH_SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    window.localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
    return null;
  }
}

export function getStoredSessionEmail(): string | null {
  return getStoredAuthSession()?.user.email ?? null;
}

export function clearStoredAuth() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
  }
}

export async function loginWithPassword(payload: AuthCredentials): Promise<AuthSession> {
  const response = await authRequest<AuthSessionResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(normalizeCredentials(payload)),
  });

  return persistSession(buildSession(response));
}

export async function registerWithPassword(payload: AuthCredentials): Promise<AuthSession> {
  const response = await authRequest<AuthSessionResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(normalizeCredentials(payload)),
  });

  return persistSession(buildSession(response));
}

export async function fetchCurrentSession(): Promise<AuthSession> {
  const response = await authRequest<AuthSessionResponse>("/api/v1/auth/me", { method: "GET" });
  return persistSession(buildSession(response));
}

export async function logoutCurrentSession(): Promise<void> {
  await authRequest<null>("/api/v1/auth/logout", { method: "POST" });
}

export function isAuthApiError(error: unknown): error is AuthApiError {
  return error instanceof AuthApiError;
}
