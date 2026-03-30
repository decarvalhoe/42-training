import Link from "next/link";
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
} from "react";

function joinClassNames(...values: Array<string | false | null | undefined>) {
  return values.filter(Boolean).join(" ");
}

export function GuidedPanel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={joinClassNames(
        "border border-[var(--shell-border)] bg-[var(--shell-panel)]",
        className,
      )}
    >
      {children}
    </section>
  );
}

export function GuidedSidebarSection({
  label,
  children,
  className,
}: {
  label: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={joinClassNames("space-y-3", className)}>
      <p className="font-mono text-[9px] font-medium uppercase tracking-[0.3em] text-[var(--shell-dim)]">
        {label}
      </p>
      {children}
    </div>
  );
}

export function GuidedField({
  label,
  children,
  hint,
  className,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
  className?: string;
}) {
  return (
    <label className={joinClassNames("grid gap-2", className)}>
      <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
        {label}
      </span>
      {children}
      {hint ? (
        <span className="font-mono text-[10px] leading-5 text-[var(--shell-dim)]">
          {hint}
        </span>
      ) : null}
    </label>
  );
}

export function GuidedInput({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={joinClassNames(
        "min-h-11 border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-2 font-mono text-sm text-[var(--shell-ink)] outline-none transition-colors placeholder:text-[var(--shell-dim)] focus:border-[var(--shell-success)]",
        className,
      )}
      {...props}
    />
  );
}

export function GuidedSelect({
  className,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={joinClassNames(
        "min-h-11 border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-2 font-mono text-sm text-[var(--shell-ink)] outline-none transition-colors focus:border-[var(--shell-success)]",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}

export function GuidedTextarea({
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={joinClassNames(
        "min-h-[132px] w-full border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-3 font-mono text-sm leading-7 text-[var(--shell-ink)] outline-none transition-colors placeholder:text-[var(--shell-dim)] focus:border-[var(--shell-success)]",
        className,
      )}
      {...props}
    />
  );
}

export function GuidedActionButton({
  children,
  className,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  className?: string;
  variant?: "primary" | "secondary" | "danger";
}) {
  const tone =
    variant === "primary"
      ? "border-[var(--shell-success)] bg-[var(--shell-success)] text-[var(--shell-canvas)] hover:bg-[var(--shell-success-strong)]"
      : variant === "danger"
        ? "border-[var(--shell-danger)] bg-[var(--shell-danger)] text-[var(--shell-canvas)] hover:bg-[#ff6161]"
        : "border-[var(--shell-border-strong)] bg-transparent text-[var(--shell-ink)] hover:border-[var(--shell-success)] hover:text-[var(--shell-success)]";

  return (
    <button
      className={joinClassNames(
        "inline-flex min-h-10 items-center justify-center border px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.28em] transition-colors disabled:cursor-not-allowed disabled:opacity-50",
        tone,
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}

export function GuidedActionLink({
  href,
  children,
  className,
  variant = "primary",
}: {
  href: string;
  children: ReactNode;
  className?: string;
  variant?: "primary" | "secondary";
}) {
  const tone =
    variant === "primary"
      ? "border-[var(--shell-success)] bg-[var(--shell-success)] text-[var(--shell-canvas)] hover:bg-[var(--shell-success-strong)]"
      : "border-[var(--shell-border-strong)] bg-transparent text-[var(--shell-ink)] hover:border-[var(--shell-success)] hover:text-[var(--shell-success)]";

  return (
    <Link
      href={href}
      className={joinClassNames(
        "inline-flex min-h-10 items-center justify-center border px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.28em] transition-colors",
        tone,
        className,
      )}
    >
      {children}
    </Link>
  );
}

export function GuidedBadge({
  children,
  tone = "default",
}: {
  children: ReactNode;
  tone?: "default" | "success" | "warning" | "danger";
}) {
  const className =
    tone === "success"
      ? "border-[rgba(0,224,110,0.4)] text-[var(--shell-success)]"
      : tone === "warning"
        ? "border-[rgba(255,175,0,0.35)] text-[var(--shell-warning)]"
        : tone === "danger"
          ? "border-[rgba(255,65,65,0.35)] text-[var(--shell-danger)]"
          : "border-[var(--shell-border-strong)] text-[var(--shell-muted)]";

  return (
    <span
      className={joinClassNames(
        "inline-flex items-center border px-2 py-1 font-mono text-[10px] uppercase tracking-[0.24em]",
        className,
      )}
    >
      {children}
    </span>
  );
}

export function GuidedStatusBar({
  left,
  right,
}: {
  left: ReactNode;
  right: ReactNode;
}) {
  return (
    <div className="flex min-h-7 items-center justify-between gap-4 border border-[var(--shell-border)] bg-[var(--shell-sidebar)] px-5 py-2 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--shell-dim)]">
      <div className="truncate">{left}</div>
      <div className="truncate text-right">{right}</div>
    </div>
  );
}

export function GuidedEmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: ReactNode;
}) {
  return (
    <GuidedPanel className="px-6 py-6">
      <h2 className="font-mono text-lg font-semibold uppercase tracking-[0.12em] text-[var(--shell-ink)]">
        {title}
      </h2>
      <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--shell-muted)]">
        {body}
      </p>
      {action ? <div className="mt-5">{action}</div> : null}
    </GuidedPanel>
  );
}
