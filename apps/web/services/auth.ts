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

type AuthTokenResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
  learner_profile: AuthProfile | null;
  profiles: AuthProfile[];
};

type AuthMeResponse = {
  user: AuthUser;
  learner_profile: AuthProfile | null;
  profiles: AuthProfile[];
};

export type AuthSession = {
  accessToken: string;
  tokenType: "bearer";
  expiresIn: number | null;
  user: AuthUser;
  learnerProfile: AuthProfile | null;
  profiles: AuthProfile[];
};

export const ACCESS_TOKEN_STORAGE_KEY = "training-access-token";
export const AUTH_SESSION_STORAGE_KEY = "training-auth-session";
export const ACCESS_TOKEN_COOKIE_KEY = "training-access-token";

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

function buildSessionFromTokenResponse(data: AuthTokenResponse): AuthSession {
  return {
    accessToken: data.access_token,
    tokenType: data.token_type,
    expiresIn: data.expires_in,
    user: data.user,
    learnerProfile: data.learner_profile ?? null,
    profiles: data.profiles,
  };
}

function serializeSession(session: AuthSession) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, session.accessToken);
  window.localStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(session));
}

function setTokenCookie(token: string, maxAgeSeconds: number | null) {
  if (typeof document === "undefined") {
    return;
  }

  const cookieParts = [
    `${ACCESS_TOKEN_COOKIE_KEY}=${encodeURIComponent(token)}`,
    "Path=/",
    "SameSite=Lax",
  ];

  if (typeof maxAgeSeconds === "number") {
    cookieParts.push(`Max-Age=${Math.max(0, Math.floor(maxAgeSeconds))}`);
  }

  document.cookie = cookieParts.join("; ");
}

function clearTokenCookie() {
  if (typeof document === "undefined") {
    return;
  }

  document.cookie = `${ACCESS_TOKEN_COOKIE_KEY}=; Path=/; Max-Age=0; SameSite=Lax`;
}

function persistSession(session: AuthSession): AuthSession {
  serializeSession(session);
  setTokenCookie(session.accessToken, session.expiresIn);
  return session;
}

function extractErrorMessage(payload: unknown, fallback: string) {
  if (payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string") {
    return payload.detail;
  }

  return fallback;
}

async function authRequest<T>(path: string, init?: RequestInit, token?: string): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    throw new AuthApiError(
      extractErrorMessage(payload, `Authentication failed with status ${response.status}.`),
      response.status,
    );
  }

  return payload as T;
}

export function getStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
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
    return null;
  }
}

export function getStoredSessionEmail(): string | null {
  return getStoredAuthSession()?.user.email ?? null;
}

export function clearStoredAuth() {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
  }

  clearTokenCookie();
}

export async function loginWithPassword(payload: AuthCredentials): Promise<AuthSession> {
  const response = await authRequest<AuthTokenResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(normalizeCredentials(payload)),
  });

  return persistSession(buildSessionFromTokenResponse(response));
}

export async function registerWithPassword(payload: AuthCredentials): Promise<AuthSession> {
  const response = await authRequest<AuthTokenResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(normalizeCredentials(payload)),
  });

  return persistSession(buildSessionFromTokenResponse(response));
}

export async function fetchCurrentSession(accessToken = getStoredAccessToken()): Promise<AuthSession> {
  if (!accessToken) {
    throw new AuthApiError("No bearer token available.", 401);
  }

  const current = getStoredAuthSession();
  const response = await authRequest<AuthMeResponse>("/api/v1/auth/me", { method: "GET" }, accessToken);
  return persistSession({
    accessToken,
    tokenType: "bearer",
    expiresIn: current?.expiresIn ?? null,
    user: response.user,
    learnerProfile: response.learner_profile ?? null,
    profiles: response.profiles,
  });
}

export function isAuthApiError(error: unknown): error is AuthApiError {
  return error instanceof AuthApiError;
}
