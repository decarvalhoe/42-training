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

function buildPostAuthTarget(session: AuthSession, requestedNext: string) {
  if (session.learnerProfile !== null) {
    return requestedNext;
  }

  const params = new URLSearchParams({ onboarding: "1" });
  if (requestedNext !== "/" && requestedNext !== "/profiles") {
    params.set("next", requestedNext);
  }

  return `/profiles?${params.toString()}`;
}

export default function LoginPage() {
  const { login, session, status } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState<FormState>(INITIAL_STATE);
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverMessage, setServerMessage] = useState<string | null>(null);
  const [submitState, setSubmitState] = useState<"idle" | "success" | "error">(
    "idle",
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (status !== "authenticated" || session === null) {
      return;
    }

    const requestedNext =
      typeof window === "undefined"
        ? "/"
        : normalizeNextPath(
            new URLSearchParams(window.location.search).get("next"),
          );
    router.replace(buildPostAuthTarget(session, requestedNext));
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
      const nextSession = await login(form);
      const requestedNext =
        typeof window === "undefined"
          ? "/"
          : normalizeNextPath(
              new URLSearchParams(window.location.search).get("next"),
            );
      const destination = buildPostAuthTarget(nextSession, requestedNext);
      setServerMessage(`Signed in as ${nextSession.user.email}.`);
      setSubmitState("success");
      router.replace(destination);
    } catch (error) {
      setServerMessage(
        isAuthApiError(error)
          ? error.message
          : "The login flow failed unexpectedly.",
      );
      setSubmitState("error");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-[var(--shell-canvas)] text-[var(--shell-ink)]">
      <section className="grid min-h-screen lg:grid-cols-[720px_1px_1fr]">
        {/* Left — ASCII Branding */}
        <div className="flex min-h-[44vh] flex-col items-center justify-center gap-8 overflow-hidden px-8 py-14 lg:min-h-screen lg:px-16 lg:py-16">
          <div className="font-mono text-[18px] font-bold leading-[22px] text-[var(--shell-success)]">
            {ASCII_LOGO.map((line) => (
              <p key={line} className="whitespace-pre">
                {line}
              </p>
            ))}
          </div>

          <p className="font-mono text-[14px] tracking-[0.55em] text-[var(--shell-muted)]">
            TRAINING PLATFORM
          </p>

          <div className="space-y-1 font-mono text-[12px] leading-6 text-[var(--shell-dim)]">
            {BOOT_LINES.map((line) => (
              <p key={line} className="whitespace-pre">
                {line}
              </p>
            ))}
          </div>
        </div>

        {/* Divider */}
        <div className="hidden bg-[var(--shell-success)]/25 lg:block" />

        {/* Right — Auth Form */}
        <section className="flex min-h-[56vh] flex-col justify-center bg-[var(--shell-panel)] px-6 py-12 sm:px-12 lg:min-h-screen lg:px-[120px]">
          <div className="mx-auto flex w-full max-w-[479px] flex-col items-center">
            <p className="font-mono text-[16px] font-bold text-[var(--shell-success)]">
              $ ssh learner@42training
            </p>
            <p className="mt-5 font-mono text-[12px] text-[var(--shell-muted)]">
              authenticate to continue
            </p>

            {/* Spacer */}
            <div className="mt-8 h-4 w-full" />

            <form
              className="login-form flex w-full flex-col gap-5"
              noValidate
              onSubmit={handleSubmit}
            >
              {/* EMAIL */}
              <label className="flex flex-col gap-3">
                <span className="text-center font-mono text-[10px] font-medium uppercase tracking-[0.45em] text-[var(--shell-muted)]">
                  Email
                </span>
                <input
                  className="h-12 border border-[var(--shell-border)] bg-[var(--shell-canvas)]/60 px-4 font-mono text-[13px] text-[var(--shell-ink)] outline-none transition-colors placeholder:text-[var(--shell-muted)] focus:border-[var(--shell-success)]"
                  type="email"
                  name="email"
                  autoComplete="email"
                  placeholder="> learner@student.42lausanne.ch"
                  value={form.email}
                  onChange={(event) => updateField("email", event.target.value)}
                  aria-invalid={Boolean(errors.email)}
                  aria-describedby={
                    errors.email ? "login-email-error" : undefined
                  }
                />
                {errors.email ? (
                  <small
                    id="login-email-error"
                    className="font-mono text-[11px] text-[var(--shell-danger)]"
                  >
                    {errors.email}
                  </small>
                ) : null}
              </label>

              {/* PASSWORD */}
              <label className="flex flex-col gap-3">
                <span className="text-center font-mono text-[10px] font-medium uppercase tracking-[0.45em] text-[var(--shell-muted)]">
                  Password
                </span>
                <input
                  className="h-12 border border-[var(--shell-border)] bg-[var(--shell-canvas)]/60 px-4 font-mono text-[13px] text-[var(--shell-ink)] outline-none transition-colors placeholder:text-[var(--shell-muted)] focus:border-[var(--shell-success)]"
                  type="password"
                  name="password"
                  autoComplete="current-password"
                  placeholder="> ••••••••••••"
                  value={form.password}
                  onChange={(event) =>
                    updateField("password", event.target.value)
                  }
                  aria-invalid={Boolean(errors.password)}
                  aria-describedby={
                    errors.password ? "login-password-error" : undefined
                  }
                />
                {errors.password ? (
                  <small
                    id="login-password-error"
                    className="font-mono text-[11px] text-[var(--shell-danger)]"
                  >
                    {errors.password}
                  </small>
                ) : null}
              </label>

              {/* Spacer */}
              <div className="h-2" />

              {/* Single CTA — canonical */}
              <button
                type="submit"
                aria-label="Sign in"
                className="flex h-[52px] items-center justify-center bg-[var(--shell-success)] px-6 font-mono text-[14px] font-bold uppercase tracking-[0.3em] text-[var(--shell-canvas)] transition-colors hover:bg-[var(--shell-success-strong)] disabled:cursor-not-allowed disabled:opacity-60"
                disabled={isSubmitting}
              >
                {isSubmitting ? "[ AUTHENTICATING ]" : "[ AUTHENTICATE ]"}
              </button>
            </form>

            {/* Server message */}
            {serverMessage ? (
              <div
                className={[
                  "mt-5 w-full border px-4 py-3 font-mono text-[11px] leading-5",
                  submitState === "success"
                    ? "border-[var(--shell-success)]/35 bg-[var(--shell-success)]/10 text-[#b5ffcf]"
                    : "border-[var(--shell-danger)]/35 bg-[var(--shell-danger)]/10 text-[#ffd0d0]",
                ].join(" ")}
                aria-live="polite"
              >
                {serverMessage}
              </div>
            ) : null}

            {/* Footer runtime strip */}
            <p className="mt-5 text-center font-mono text-[10px] text-[var(--shell-dim)]">
              42-training v1.0 // jwt:hs256 // session:15m //
              tmux:learn42+mentor42
            </p>
          </div>
        </section>
      </section>
    </main>
  );
}
