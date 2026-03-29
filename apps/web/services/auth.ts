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

  return {
    ok: true,
    message: `Signed in as ${email}. Backend auth is not wired yet, so this is a mocked response.`,
    mocked: true,
  };
}
