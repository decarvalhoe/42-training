export type LoginPayload = {
  email: string;
  password: string;
};

export type LoginResult = {
  ok: boolean;
  message: string;
  mocked: true;
};

const MOCK_LATENCY_MS = 700;
export const MOCK_SESSION_EMAIL_KEY = "training-mock-user-email";
export const ACCESS_TOKEN_STORAGE_KEY = "training-access-token";

function persistMockSessionEmail(email: string) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(MOCK_SESSION_EMAIL_KEY, email);
}

export function getMockSessionEmail(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(MOCK_SESSION_EMAIL_KEY);
}

export function getStoredAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }

  return window.localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
}

export async function loginWithPassword(payload: LoginPayload): Promise<LoginResult> {
  await new Promise((resolve) => setTimeout(resolve, MOCK_LATENCY_MS));

  const email = payload.email.trim().toLowerCase();

  if (email === "blocked@42lausanne.ch") {
    return {
      ok: false,
      message: "This demo account is blocked in the mocked auth service.",
      mocked: true,
    };
  }

  persistMockSessionEmail(email);

  return {
    ok: true,
    message: `Signed in as ${email}. Backend auth is not wired yet, so this is a mocked response.`,
    mocked: true,
  };
}
