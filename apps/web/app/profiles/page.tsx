"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/app/components/AuthProvider";
import { getDashboardData, type TrackItem } from "@/lib/api";
import {
  createProfile,
  listProfiles,
  switchActiveProfile,
  type ProfileItem,
  type ProfilesState,
} from "@/services/profiles";

type ProfileFormState = {
  track: string;
  login: string;
};

type FormErrors = Partial<Record<keyof ProfileFormState, string>>;

const INITIAL_FORM: ProfileFormState = {
  track: "",
  login: "",
};

function validateProfileForm(values: ProfileFormState): FormErrors {
  const errors: FormErrors = {};

  if (!values.track) {
    errors.track = "Select a track for the new profile.";
  }

  if (values.login.trim() && !/^[a-z0-9-]+$/i.test(values.login.trim())) {
    errors.login =
      "Use only letters, numbers or hyphens for the optional login.";
  }

  return errors;
}

function formatTrackTitle(trackId: string, tracks: TrackItem[]) {
  return tracks.find((track) => track.id === trackId)?.title ?? trackId;
}

function formatDateLabel(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function normalizeNextPath(value: string | null) {
  if (!value || !value.startsWith("/") || value.startsWith("//")) {
    return "/dashboard";
  }

  if (value === "/profiles") {
    return "/dashboard";
  }

  return value;
}

export default function ProfilesPage() {
  const { refreshSession, session } = useAuth();
  const [tracks, setTracks] = useState<TrackItem[]>([]);
  const [profilesState, setProfilesState] = useState<ProfilesState | null>(
    null,
  );
  const [form, setForm] = useState<ProfileFormState>(INITIAL_FORM);
  const [errors, setErrors] = useState<FormErrors>({});
  const [loadingState, setLoadingState] = useState<
    "loading" | "ready" | "error"
  >("loading");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [feedbackTone, setFeedbackTone] = useState<"success" | "error">(
    "success",
  );
  const [isCreating, setIsCreating] = useState(false);
  const [switchingId, setSwitchingId] = useState<string | null>(null);
  const [searchState, setSearchState] = useState({
    onboarding: false,
    source: null as string | null,
    next: "/dashboard",
  });

  const loadPage = useCallback(async (cancelledRef?: { current: boolean }) => {
    setLoadingState("loading");

    try {
      const [dashboard, profiles] = await Promise.all([
        getDashboardData(),
        listProfiles(),
      ]);
      if (cancelledRef?.current) {
        return;
      }

      setTracks(dashboard.curriculum.tracks);
      setProfilesState(profiles);
      setForm((current) => ({
        ...current,
        track: current.track || dashboard.curriculum.tracks[0]?.id || "",
      }));
      setLoadingState("ready");
    } catch {
      if (!cancelledRef?.current) {
        setLoadingState("error");
      }
    }
  }, []);

  useEffect(() => {
    const cancelledRef = { current: false };
    void loadPage(cancelledRef);

    return () => {
      cancelledRef.current = true;
    };
  }, [loadPage]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    setSearchState({
      onboarding: params.get("onboarding") === "1",
      source: params.get("source"),
      next: normalizeNextPath(params.get("next")),
    });
  }, []);

  const activeProfile = profilesState?.activeProfile ?? null;
  const sessionEmail = session?.user.email ?? "Authenticated learner";
  const continueHref = searchState.next;
  const isOnboarding = searchState.onboarding || activeProfile === null;
  const onboardingSource = searchState.source;
  const onboardingComplete = isOnboarding && activeProfile !== null;
  const hasProfiles = (profilesState?.profiles.length ?? 0) > 0;

  function updateField(field: keyof ProfileFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
    setFeedback(null);
  }

  async function handleCreateProfile(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const nextErrors = validateProfileForm(form);
    setErrors(nextErrors);
    setFeedback(null);
    if (Object.keys(nextErrors).length > 0) {
      setFeedbackTone("error");
      return;
    }

    setIsCreating(true);
    try {
      const nextState = await createProfile({
        track: form.track,
        login: form.login.trim() || undefined,
      });
      setProfilesState(nextState);
      await refreshSession().catch(() => undefined);
      setForm((current) => ({ ...current, login: "" }));
      setFeedbackTone("success");
      setFeedback(
        isOnboarding
          ? `Profile for ${formatTrackTitle(form.track, tracks)} is ready and now active. Continue into the workspace when you are ready.`
          : `Profile for ${formatTrackTitle(form.track, tracks)} is ready and now active.`,
      );
    } catch (error) {
      setFeedbackTone("error");
      setFeedback(
        error instanceof Error
          ? error.message
          : "Unable to create a new profile.",
      );
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSwitchProfile(profile: ProfileItem) {
    setFeedback(null);
    setSwitchingId(profile.id);
    try {
      const nextState = await switchActiveProfile(profile.id);
      setProfilesState(nextState);
      await refreshSession().catch(() => undefined);
      setFeedbackTone("success");
      setFeedback(
        isOnboarding
          ? `${formatTrackTitle(profile.track, tracks)} is now the active profile. Continue into the workspace when you are ready.`
          : `${formatTrackTitle(profile.track, tracks)} is now the active profile.`,
      );
    } catch (error) {
      setFeedbackTone("error");
      setFeedback(
        error instanceof Error
          ? error.message
          : "Unable to switch the active profile.",
      );
    } finally {
      setSwitchingId(null);
    }
  }

  if (loadingState === "loading") {
    return (
      <main className="grid gap-6">
        <section className="border border-[var(--shell-border)] bg-[var(--shell-panel)] p-6 lg:p-8">
          <p className="font-mono text-[11px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
            {isOnboarding ? "First-run onboarding" : "Profiles"}
          </p>
          <h1 className="mt-3 font-mono text-3xl uppercase tracking-[0.08em] text-[var(--shell-ink)]">
            Loading profile workspace...
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--shell-muted)]">
            Preparing the available tracks and the current active learner
            context.
          </p>
        </section>
      </main>
    );
  }

  if (loadingState === "error" || profilesState === null) {
    return (
      <main className="grid gap-6">
        <section className="border border-[var(--shell-border)] bg-[var(--shell-panel)] p-6 lg:p-8">
          <p className="font-mono text-[11px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
            Profiles
          </p>
          <h1 className="mt-3 font-mono text-3xl uppercase tracking-[0.08em] text-[var(--shell-ink)]">
            Profile management is temporarily unavailable.
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--shell-muted)]">
            The UI could not load the profile catalog. Refresh the page or
            return to the dashboard.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              className="inline-flex items-center border border-[var(--shell-success)] bg-[var(--shell-success)] px-4 py-3 font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--shell-canvas)]"
              onClick={() => void loadPage()}
            >
              Retry
            </button>
            <Link
              href="/dashboard"
              className="inline-flex items-center border border-[var(--shell-border-strong)] px-4 py-3 font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--shell-ink)]"
            >
              Back to dashboard
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const heroTitle = onboardingComplete
    ? `${formatTrackTitle(activeProfile.track, tracks)} is now active.`
    : isOnboarding
      ? "Choose your first learning track."
      : "Manage learner profiles and active context.";

  const heroLead = onboardingComplete
    ? "The learner context is ready. Continue to the workspace and start the next module with a clear active profile."
    : isOnboarding
      ? "A fresh account needs one active learner profile before the guided learning flow can begin. Create or activate a track now."
      : "Use separate profiles to isolate progression across Shell, C and Python + AI while keeping a single authenticated account.";

  return (
    <main className="grid gap-6">
      <section className="grid gap-6 border border-[var(--shell-border)] bg-[var(--shell-panel)] p-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(320px,0.8fr)] lg:p-8">
        <div>
          <p className="font-mono text-[11px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
            {onboardingComplete
              ? "Onboarding complete"
              : isOnboarding
                ? "First-run onboarding"
                : "Profiles"}
          </p>
          <h1 className="mt-3 font-mono text-3xl uppercase tracking-[0.08em] text-[var(--shell-ink)]">
            {heroTitle}
          </h1>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-[var(--shell-muted)]">
            {heroLead}
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
                Connected user
              </p>
              <p className="mt-2 break-all font-mono text-xs uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                {sessionEmail}
              </p>
            </div>
            <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
                Active profile
              </p>
              <p className="mt-2 font-mono text-xs uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                {activeProfile
                  ? formatTrackTitle(activeProfile.track, tracks)
                  : "Not selected yet"}
              </p>
            </div>
            <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
                Profiles linked
              </p>
              <p className="mt-2 font-mono text-xs uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                {profilesState.profiles.length}
              </p>
            </div>
            <div className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-muted)]">
                Data source
              </p>
              <p className="mt-2 font-mono text-xs uppercase tracking-[0.12em] text-[var(--shell-ink)]">
                {profilesState.mocked ? "Demo mode" : "API live state"}
              </p>
            </div>
          </div>

          {feedback ? (
            <div
              className={[
                "mt-6 border px-4 py-4 font-mono text-[11px] leading-6",
                feedbackTone === "success"
                  ? "border-[var(--shell-success)]/35 bg-[var(--shell-success)]/10 text-[var(--shell-ink)]"
                  : "border-[var(--shell-danger)]/35 bg-[var(--shell-danger)]/10 text-[var(--shell-danger)]",
              ].join(" ")}
              aria-live="polite"
            >
              {feedback}
            </div>
          ) : null}
        </div>

        <aside className="border border-[var(--shell-border)] bg-[var(--shell-canvas)] p-5">
          <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-[var(--shell-success)]">
            {isOnboarding ? "Next steps" : "Profile guide"}
          </p>
          <div className="mt-4 space-y-4 text-sm leading-7 text-[var(--shell-muted)]">
            <div className="border border-[var(--shell-border)] px-4 py-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-ink)]">
                1. Create or pick a track
              </p>
              <p className="mt-2">
                {hasProfiles
                  ? "You can activate an existing profile or create a new one for another track."
                  : "Start by creating the first learner profile attached to this account."}
              </p>
            </div>
            <div className="border border-[var(--shell-border)] px-4 py-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-ink)]">
                2. Confirm the active context
              </p>
              <p className="mt-2">
                The active profile becomes the learner scope used by modules,
                review, mentor and defense.
              </p>
            </div>
            <div className="border border-[var(--shell-border)] px-4 py-3">
              <p className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-ink)]">
                3. Continue into the workspace
              </p>
              <p className="mt-2">
                {onboardingSource === "register"
                  ? "This account was just created, so the next action is to activate the first track."
                  : "Once the active profile is set, continue to the dashboard or the requested page."}
              </p>
            </div>

            {onboardingComplete ? (
              <Link
                href={continueHref}
                className="inline-flex w-full items-center justify-center border border-[var(--shell-success)] bg-[var(--shell-success)] px-4 py-3 font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--shell-canvas)]"
              >
                Continue to workspace
              </Link>
            ) : null}
          </div>
        </aside>
      </section>

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_420px]">
        <article className="border border-[var(--shell-border)] bg-[var(--shell-panel)] p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-mono text-[11px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
                {isOnboarding ? "Step 2" : "Selection"}
              </p>
              <h2 className="mt-2 font-mono text-2xl uppercase tracking-[0.08em] text-[var(--shell-ink)]">
                Active learner context
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-7 text-[var(--shell-muted)]">
                Switch between existing profiles when you want to move from one
                track to another without mixing progression.
              </p>
            </div>
            <Link
              href="/dashboard"
              className="inline-flex items-center border border-[var(--shell-border-strong)] px-4 py-3 font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--shell-ink)]"
            >
              Back to dashboard
            </Link>
          </div>

          {profilesState.profiles.length === 0 ? (
            <div className="mt-6 border border-dashed border-[var(--shell-border)] px-5 py-6 text-sm leading-7 text-[var(--shell-muted)]">
              No learner profile exists yet. Create one in the right panel to
              unlock the guided learning flow.
            </div>
          ) : (
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              {profilesState.profiles.map((profile) => {
                const isActive = profile.id === profilesState.activeProfileId;

                return (
                  <article
                    key={profile.id}
                    className={[
                      "border px-5 py-5 transition-colors",
                      isActive
                        ? "border-[var(--shell-success)] bg-[var(--shell-success)]/5"
                        : "border-[var(--shell-border)] bg-[var(--shell-canvas)]",
                    ].join(" ")}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-[var(--shell-muted)]">
                        {profile.track}
                      </p>
                      <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-[var(--shell-ink)]">
                        {isActive ? "Active" : "Inactive"}
                      </span>
                    </div>
                    <h3 className="mt-3 font-mono text-lg uppercase tracking-[0.08em] text-[var(--shell-ink)]">
                      {formatTrackTitle(profile.track, tracks)}
                    </h3>
                    <p className="mt-3 text-sm text-[var(--shell-muted)]">
                      Login handle: {profile.login}
                    </p>
                    <div className="mt-4 space-y-2 text-sm text-[var(--shell-muted)]">
                      <p>Started {formatDateLabel(profile.startedAt)}</p>
                      <p>
                        {profile.currentModule
                          ? `Current module: ${profile.currentModule}`
                          : "No module selected yet"}
                      </p>
                    </div>
                    <button
                      type="button"
                      className={[
                        "mt-5 inline-flex w-full items-center justify-center border px-4 py-3 font-mono text-[11px] uppercase tracking-[0.28em]",
                        isActive
                          ? "border-[var(--shell-border)] text-[var(--shell-muted)]"
                          : "border-[var(--shell-success)] bg-[var(--shell-success)] text-[var(--shell-canvas)]",
                      ].join(" ")}
                      onClick={() => void handleSwitchProfile(profile)}
                      disabled={isActive || switchingId === profile.id}
                    >
                      {isActive
                        ? "Active profile"
                        : switchingId === profile.id
                          ? "Switching..."
                          : "Set active"}
                    </button>
                  </article>
                );
              })}
            </div>
          )}
        </article>

        <aside className="border border-[var(--shell-border)] bg-[var(--shell-panel)] p-6">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.32em] text-[var(--shell-success)]">
              {isOnboarding ? "Step 1" : "Creation"}
            </p>
            <h2 className="mt-2 font-mono text-2xl uppercase tracking-[0.08em] text-[var(--shell-ink)]">
              Add a track profile
            </h2>
            <p className="mt-3 text-sm leading-7 text-[var(--shell-muted)]">
              One profile per track. Use the optional login field if you want a
              custom handle instead of the generated one.
            </p>
          </div>

          <form
            className="profiles-form mt-6 flex flex-col gap-5"
            noValidate
            onSubmit={handleCreateProfile}
          >
            <label className="flex flex-col gap-3">
              <span className="font-mono text-[10px] uppercase tracking-[0.35em] text-[var(--shell-muted)]">
                Track
              </span>
              <select
                className="h-12 rounded-none border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 font-mono text-[12px] uppercase tracking-[0.16em] text-[var(--shell-ink)] outline-none focus:border-[var(--shell-success)]"
                value={form.track}
                onChange={(event) => updateField("track", event.target.value)}
                aria-invalid={Boolean(errors.track)}
              >
                <option value="">Select a track</option>
                {tracks.map((track) => (
                  <option key={track.id} value={track.id}>
                    {track.title}
                  </option>
                ))}
              </select>
              {errors.track ? (
                <small className="font-mono text-[11px] text-[var(--shell-danger)]">
                  {errors.track}
                </small>
              ) : null}
            </label>

            <label className="flex flex-col gap-3">
              <span className="font-mono text-[10px] uppercase tracking-[0.35em] text-[var(--shell-muted)]">
                Custom login handle (optional)
              </span>
              <input
                className="h-12 rounded-none border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 font-mono text-[13px] text-[var(--shell-ink)] outline-none placeholder:text-[var(--shell-muted)] focus:border-[var(--shell-success)]"
                type="text"
                name="login"
                placeholder="learner-shell"
                value={form.login}
                onChange={(event) => updateField("login", event.target.value)}
                aria-invalid={Boolean(errors.login)}
              />
              {errors.login ? (
                <small className="font-mono text-[11px] text-[var(--shell-danger)]">
                  {errors.login}
                </small>
              ) : null}
            </label>

            <button
              type="submit"
              className="inline-flex items-center justify-center border border-[var(--shell-success)] bg-[var(--shell-success)] px-4 py-3 font-mono text-[11px] uppercase tracking-[0.28em] text-[var(--shell-canvas)] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={isCreating}
            >
              {isCreating ? "Creating profile..." : "Create profile"}
            </button>
          </form>

          <div className="mt-6 border border-[var(--shell-border)] bg-[var(--shell-canvas)] px-4 py-4 text-sm leading-7 text-[var(--shell-muted)]">
            <strong className="block font-mono text-[10px] uppercase tracking-[0.28em] text-[var(--shell-ink)]">
              Current integration state
            </strong>
            <p className="mt-2">
              This page uses the authenticated session cookie and the live{" "}
              <code>/api/v1/profiles</code> endpoints. Browser-backed mock data
              is available only when explicit demo mode is enabled.
            </p>
          </div>
        </aside>
      </section>
    </main>
  );
}
