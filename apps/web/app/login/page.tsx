"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/app/components/AuthProvider";
import { isAuthApiError, type AuthSession } from "@/services/auth";

type FormState = {
  email: string;
  password: string;
};

type FormErrors = Partial<Record<keyof FormState, string>>;

const INITIAL_STATE: FormState = {
  email: "",
  password: "",
};

const ASCII_LOGO = [
  "    ██╗  ██╗██████╗ ",
  "    ██║  ██║╚════██╗",
  "    ███████║ █████╔╝",
  "    ╚════██║██╔═══╝ ",
  "         ██║███████╗",
  "         ╚═╝╚══════╝",
];

const BOOT_LINES = [
  "> system boot ............ [OK]",
  "> loading curriculum ..... [OK]",
  "> ai_gateway ............. [OK]",
  "> redis cache ............ [OK]",
  "> creating learn42 ....... [OK]",
  ">   window: work ......... [OK]",
  ">   window: build ........ [OK]",
  ">   window: tests ........ [OK]",
  "> creating mentor42 ...... [OK]",
  "> watch_mentor ........... [OK]",
  "> waiting for auth ....... [  ]",
];

function normalizeNextPath(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/";
  }

  return value;
}

function validateLoginForm(values: FormState): FormErrors {
  const errors: FormErrors = {};

  if (!values.email.trim()) {
    errors.email = "Email is required.";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email)) {
    errors.email = "Enter a valid email address.";
  }

  if (!values.password) {
    errors.password = "Password is required.";
  } else if (values.password.length < 8) {
    errors.password = "Password must contain at least 8 characters.";
  }

  return errors;
}

function buildPostAuthTarget(session: AuthSession, requestedNext: string, source: "login" | "register" | "resume") {
  if (session.learnerProfile !== null) {
    return requestedNext;
  }

  const params = new URLSearchParams({ onboarding: "1" });
  if (source === "register") {
    params.set("source", "register");
  }
  if (requestedNext !== "/" && requestedNext !== "/profiles") {
    params.set("next", requestedNext);
  }

  return `/profiles?${params.toString()}`;
}

export default function LoginPage() {
  const { login, register, session, status } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState<FormState>(INITIAL_STATE);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverMessage, setServerMessage] = useState<string | null>(null);
  const [submitState, setSubmitState] = useState<"idle" | "success" | "error">("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (status !== "authenticated" || session === null) {
      return;
    }

    const requestedNext =
      typeof window === "undefined" ? "/" : normalizeNextPath(new URLSearchParams(window.location.search).get("next"));
    router.replace(buildPostAuthTarget(session, requestedNext, "resume"));
    router.refresh();
  }, [router, session, status]);

  function updateField(field: keyof FormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    setServerMessage(null);
    setSubmitState("idle");
  }

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors = validateLoginForm(form);
    setErrors(nextErrors);
    setServerMessage(null);

    if (Object.keys(nextErrors).length > 0) {
      setSubmitState("error");
      return;
    }

    setIsSubmitting(true);

    try {
      const nextSession = mode === "login" ? await login(form) : await register(form);
      const requestedNext =
        typeof window === "undefined" ? "/" : normalizeNextPath(new URLSearchParams(window.location.search).get("next"));
      const destination = buildPostAuthTarget(nextSession, requestedNext, mode);
      setServerMessage(
        mode === "login"
          ? `Signed in as ${nextSession.user.email}.`
          : `Account created for ${nextSession.user.email}. Redirecting to profile setup...`,
      );
      setSubmitState("success");
      router.replace(destination);
      router.refresh();
    } catch (error) {
      setServerMessage(
        isAuthApiError(error)
          ? error.message
          : `The ${mode === "login" ? "login" : "registration"} flow failed unexpectedly.`,
      );
      setSubmitState("error");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#111114] text-[#e0e4e9]">
      <section className="grid min-h-screen lg:grid-cols-[minmax(0,720px)_1px_minmax(0,1fr)]">
        <div className="flex min-h-[44vh] flex-col items-center justify-center gap-8 overflow-hidden px-8 py-14 lg:min-h-screen lg:px-16 lg:py-16">
          <div className="font-mono text-[18px] font-bold leading-[22px] text-[#00e06e]">
            {ASCII_LOGO.map((line) => (
              <p key={line} className="whitespace-pre">
                {line}
              </p>
            ))}
          </div>

          <p className="font-mono text-[14px] tracking-[0.55em] text-[#808690]">TRAINING PLATFORM</p>

          <div className="space-y-1 font-mono text-[12px] leading-6 text-[#50545c]">
            {BOOT_LINES.map((line) => (
              <p key={line} className="whitespace-pre">
                {line}
              </p>
            ))}
          </div>
        </div>

        <div className="hidden bg-[rgba(0,224,110,0.25)] lg:block" />

        <section className="flex min-h-[56vh] flex-col justify-center bg-[#191a1e] px-6 py-12 sm:px-12 lg:min-h-screen lg:px-[120px]">
          <div className="mx-auto flex w-full max-w-[479px] flex-col items-center">
            <p className="font-mono text-[16px] font-bold text-[#00e06e]">$ ssh learner@42training</p>
            <p className="mt-5 font-mono text-[12px] text-[#808690]">authenticate to continue</p>

            <div
              className="mt-8 inline-flex w-full items-center rounded-none border border-[#2d2f36] bg-[#111114] p-1"
              aria-label="Authentication mode"
            >
              <button
                type="button"
                className={[
                  "flex-1 rounded-none px-4 py-2 font-mono text-[11px] uppercase tracking-[0.35em] transition-colors",
                  mode === "login" ? "bg-[#00e06e] text-[#111114]" : "text-[#808690] hover:text-[#e0e4e9]",
                ].join(" ")}
                onClick={() => setMode("login")}
                aria-pressed={mode === "login"}
              >
                Sign in
              </button>
              <button
                type="button"
                className={[
                  "flex-1 rounded-none px-4 py-2 font-mono text-[11px] uppercase tracking-[0.35em] transition-colors",
                  mode === "register" ? "bg-[#00e06e] text-[#111114]" : "text-[#808690] hover:text-[#e0e4e9]",
                ].join(" ")}
                onClick={() => setMode("register")}
                aria-pressed={mode === "register"}
              >
                Create account
              </button>
            </div>

            <form className="login-form mt-10 flex w-full flex-col gap-5" noValidate onSubmit={handleSubmit}>
              <label className="flex flex-col gap-3">
                <span className="text-center font-mono text-[10px] font-medium uppercase tracking-[0.45em] text-[#808690]">
                  Email
                </span>
                <input
                  className="h-12 rounded-none border border-[#2d2f36] bg-[#222328] px-4 font-mono text-[13px] text-[#e0e4e9] outline-none transition-colors placeholder:text-[#808690] focus:border-[#00e06e]"
                  type="email"
                  name="email"
                  autoComplete="email"
                  placeholder="> learner@student.42lausanne.ch"
                  value={form.email}
                  onChange={(event) => updateField("email", event.target.value)}
                  aria-invalid={Boolean(errors.email)}
                  aria-describedby={errors.email ? "login-email-error" : undefined}
                />
                {errors.email ? (
                  <small id="login-email-error" className="font-mono text-[11px] text-[#ff7a7a]">
                    {errors.email}
                  </small>
                ) : null}
              </label>

              <label className="flex flex-col gap-3">
                <span className="text-center font-mono text-[10px] font-medium uppercase tracking-[0.45em] text-[#808690]">
                  Password
                </span>
                <input
                  className="h-12 rounded-none border border-[#2d2f36] bg-[#222328] px-4 font-mono text-[13px] text-[#e0e4e9] outline-none transition-colors placeholder:text-[#808690] focus:border-[#00e06e]"
                  type="password"
                  name="password"
                  autoComplete={mode === "login" ? "current-password" : "new-password"}
                  placeholder="> ••••••••••••"
                  value={form.password}
                  onChange={(event) => updateField("password", event.target.value)}
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={errors.password ? "login-password-error" : undefined}
                />
                {errors.password ? (
                  <small id="login-password-error" className="font-mono text-[11px] text-[#ff7a7a]">
                    {errors.password}
                  </small>
                ) : null}
              </label>

              <div className="h-2" />

              <button
                type="submit"
                aria-label={mode === "login" ? "Sign in" : "Create account"}
                className="flex h-[52px] items-center justify-center rounded-none bg-[#00e06e] px-6 font-mono text-[14px] font-bold uppercase tracking-[0.3em] text-[#111114] transition-colors hover:bg-[#25ee85] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isSubmitting}
              >
                {isSubmitting
                  ? mode === "login"
                    ? "[ AUTHENTICATING ]"
                    : "[ CREATING ACCOUNT ]"
                  : mode === "login"
                    ? "[ AUTHENTICATE ]"
                    : "[ CREATE ACCOUNT ]"}
              </button>
            </form>

            {serverMessage ? (
              <div
                className={[
                  "mt-5 w-full border px-4 py-3 font-mono text-[11px] leading-5",
                  submitState === "success"
                    ? "border-[#00e06e]/35 bg-[#00e06e]/10 text-[#b5ffcf]"
                    : "border-[#ff7a7a]/35 bg-[#ff7a7a]/10 text-[#ffd0d0]",
                ].join(" ")}
                aria-live="polite"
              >
                {serverMessage}
              </div>
            ) : null}

            <p className="mt-5 text-center font-mono text-[10px] text-[#50545c]">
              42-training v1.0 // jwt:hs256 // session:15m // tmux:learn42+mentor42
            </p>
          </div>
        </section>
      </section>
    </main>
  );
}
