"use client";

import Link from "next/link";
import { useState } from "react";

import { loginWithPassword } from "@/services/auth";

type FormState = {
  email: string;
  password: string;
};

type FormErrors = Partial<Record<keyof FormState, string>>;

const INITIAL_STATE: FormState = {
  email: "",
  password: "",
};

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
  const [form, setForm] = useState<FormState>(INITIAL_STATE);
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
      const result = await loginWithPassword(form);
      setServerMessage(result.message);
      setSubmitState(result.ok ? "success" : "error");
    } catch {
      setServerMessage("The mocked login flow failed unexpectedly.");
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
            The backend authentication flow is still in progress. This page validates client-side inputs
            and uses a mocked password login so the web flow can be integrated now.
          </p>
          <div className="login-highlights">
            <div className="login-highlight">
              <strong>Email + password</strong>
              <span className="muted">No API key exposed in the browser.</span>
            </div>
            <div className="login-highlight">
              <strong>Client validation</strong>
              <span className="muted">Checks email format and a minimal password length.</span>
            </div>
            <div className="login-highlight">
              <strong>Mocked backend call</strong>
              <span className="muted">Ready to swap with the real API when auth endpoints exist.</span>
            </div>
          </div>
          <p className="muted">
            Demo note: use any valid email and a password of at least 8 characters. The address
            <span className="prog-code"> blocked@42lausanne.ch </span>
            returns a mocked failure state.
          </p>
        </article>

        <section className="login-card panel" aria-labelledby="login-form-title">
          <div className="login-card-header">
            <p className="eyebrow">Web Login</p>
            <h2 id="login-form-title">Access 42-training</h2>
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
                autoComplete="current-password"
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
                {isSubmitting ? "Signing in..." : "Sign in"}
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
