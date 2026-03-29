"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/app/components/AuthProvider";
import { isAuthApiError } from "@/services/auth";

type FormState = {
  email: string;
  password: string;
};

type FormErrors = Partial<Record<keyof FormState, string>>;

const INITIAL_STATE: FormState = {
  email: "",
  password: "",
};

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

export default function LoginPage() {
  const { login, register } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState<FormState>(INITIAL_STATE);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [errors, setErrors] = useState<FormErrors>({});
  const [serverMessage, setServerMessage] = useState<string | null>(null);
  const [submitState, setSubmitState] = useState<"idle" | "success" | "error">("idle");
  const [isSubmitting, setIsSubmitting] = useState(false);

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
      const session = mode === "login" ? await login(form) : await register(form);
      const nextTarget =
        typeof window === "undefined" ? "/" : normalizeNextPath(new URLSearchParams(window.location.search).get("next"));
      setServerMessage(
        mode === "login"
          ? `Signed in as ${session.user.email}.`
          : `Account created for ${session.user.email}. Redirecting to your workspace...`,
      );
      setSubmitState("success");
      router.replace(nextTarget);
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
    <main className="page-shell login-page">
      <section className="login-shell">
        <article className="login-copy panel">
          <p className="eyebrow">Authentication</p>
          <h1>Sign in with your learner account.</h1>
          <p className="lead">
            The web app now calls the real authentication endpoints, stores the JWT locally and reuses it to
            protect the learning workspace.
          </p>
          <div className="login-highlights">
            <div className="login-highlight">
              <strong>Real API flow</strong>
              <span className="muted">Uses `/auth/login`, `/auth/register` and `/auth/me`.</span>
            </div>
            <div className="login-highlight">
              <strong>Client validation</strong>
              <span className="muted">Checks email format and a minimal password length.</span>
            </div>
            <div className="login-highlight">
              <strong>Protected pages</strong>
              <span className="muted">Unauthenticated access is redirected back to this screen.</span>
            </div>
          </div>
          <p className="muted">
            Use an existing account to sign in, or switch to create mode to register a new learner account from
            the same screen.
          </p>
        </article>

        <section className="login-card panel" aria-labelledby="login-form-title">
          <div className="login-card-header">
            <p className="eyebrow">Web Auth</p>
            <h2 id="login-form-title">{mode === "login" ? "Access 42-training" : "Create your account"}</h2>
          </div>

          <div className="login-mode-toggle" aria-label="Authentication mode">
            <button
              type="button"
              className={`login-mode-btn ${mode === "login" ? "login-mode-btn--active" : ""}`}
              onClick={() => setMode("login")}
              aria-pressed={mode === "login"}
            >
              Sign in
            </button>
            <button
              type="button"
              className={`login-mode-btn ${mode === "register" ? "login-mode-btn--active" : ""}`}
              onClick={() => setMode("register")}
              aria-pressed={mode === "register"}
            >
              Create account
            </button>
          </div>

          <form className="login-form" noValidate onSubmit={handleSubmit}>
            <label className="login-field">
              <span>Email</span>
              <input
                type="email"
                name="email"
                autoComplete="email"
                placeholder="learner@42lausanne.ch"
                value={form.email}
                onChange={(event) => updateField("email", event.target.value)}
                aria-invalid={Boolean(errors.email)}
                aria-describedby={errors.email ? "login-email-error" : undefined}
              />
              {errors.email && (
                <small id="login-email-error" className="login-error">
                  {errors.email}
                </small>
              )}
            </label>

            <label className="login-field">
              <span>Password</span>
              <input
                type="password"
                name="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                placeholder="Minimum 8 characters"
                value={form.password}
                onChange={(event) => updateField("password", event.target.value)}
                aria-invalid={Boolean(errors.password)}
                aria-describedby={errors.password ? "login-password-error" : undefined}
              />
              {errors.password && (
                <small id="login-password-error" className="login-error">
                  {errors.password}
                </small>
              )}
            </label>

            <div className="login-actions">
              <button type="submit" className="action-btn login-submit" disabled={isSubmitting}>
                {isSubmitting
                  ? mode === "login"
                    ? "Signing in..."
                    : "Creating account..."
                  : mode === "login"
                    ? "Sign in"
                    : "Create account"}
              </button>
              <Link href="/" className="login-secondary-link">
                Back to dashboard
              </Link>
            </div>
          </form>

          {serverMessage && (
            <div
              className={`login-feedback ${
                submitState === "success" ? "login-feedback--success" : "login-feedback--error"
              }`}
              aria-live="polite"
            >
              {serverMessage}
            </div>
          )}
        </section>
      </section>
    </main>
  );
}
