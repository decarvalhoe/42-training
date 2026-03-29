export type LoginPayload = {
  email: string;
  password: string;
};

export type LearnerProfile = {
  id: string;
  login: string;
  track: string;
  current_module: string | null;
};

export type AuthUser = {
  id: string;
  email: string;
  status: string;
};

export type AuthSession = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  expires_at: number;
  user: AuthUser;
  learner_profile: LearnerProfile | null;
};

export type LoginResult = {
  ok: boolean;
  message: string;
  mocked: false;
  session: AuthSession | null;
};

type AuthApiResponse = {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: AuthUser;
  learner_profile: LearnerProfile | null;
};

const SESSION_STORAGE_KEY = "training.auth.session";

function getApiUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

function getSessionStorage(): Storage | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function toStoredSession(payload: AuthApiResponse): AuthSession {
  return {
    ...payload,
    expires_at: Date.now() + payload.expires_in * 1000,
  };
}

function saveSession(session: AuthSession): void {
  getSessionStorage()?.setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function getStoredSession(): AuthSession | null {
  const storage = getSessionStorage();
  const raw = storage?.getItem(SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    storage?.removeItem(SESSION_STORAGE_KEY);
    return null;
  }
}

export function clearStoredSession(): void {
  getSessionStorage()?.removeItem(SESSION_STORAGE_KEY);
}

async function postAuth<TResponse>(path: string, body?: unknown, token?: string): Promise<TResponse> {
  const response = await fetch(`${getApiUrl()}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    const fallbackMessage = `Authentication request failed with ${response.status}`;
    try {
      const error = (await response.json()) as { detail?: string };
      throw new Error(error.detail ?? fallbackMessage);
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error(fallbackMessage, { cause: error });
    }
  }

  return (await response.json()) as TResponse;
}

async function issueSession(path: string, body?: unknown, token?: string): Promise<AuthSession> {
  const payload = await postAuth<AuthApiResponse>(path, body, token);
  const session = toStoredSession(payload);
  saveSession(session);
  return session;
}

export async function loginWithPassword(payload: LoginPayload): Promise<LoginResult> {
  const normalizedPayload = {
    email: payload.email.trim().toLowerCase(),
    password: payload.password,
  };

  const session = await issueSession("/api/v1/auth/login", normalizedPayload);
  const profileSummary = session.learner_profile
    ? ` Active profile: ${session.learner_profile.login} (${session.learner_profile.track}).`
    : "";

  return {
    ok: true,
    message: `Signed in as ${session.user.email}.${profileSummary}`,
    mocked: false,
    session,
  };
}

export async function refreshSession(): Promise<AuthSession | null> {
  const session = getStoredSession();
  if (!session) {
    return null;
  }

  try {
    return await issueSession("/api/v1/auth/refresh", undefined, session.access_token);
  } catch {
    clearStoredSession();
    return null;
  }
}

export async function switchProfile(profileId: string): Promise<AuthSession> {
  const session = getStoredSession();
  if (!session) {
    throw new Error("No active session");
  }

  return issueSession("/api/v1/auth/switch-profile", { profile_id: profileId }, session.access_token);
}

export async function logout(): Promise<void> {
  const session = getStoredSession();
  if (session) {
    try {
      await postAuth("/api/v1/auth/logout", undefined, session.access_token);
    } catch {
      // Token logout is best-effort; local session is always cleared.
    }
  }
  clearStoredSession();
}
