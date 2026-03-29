"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { getDashboardData, type TrackItem } from "@/lib/api";
import { getMockSessionEmail } from "@/services/auth";
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
    errors.login = "Use only letters, numbers or hyphens for the optional login.";
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

export default function ProfilesPage() {
  const [tracks, setTracks] = useState<TrackItem[]>([]);
  const [profilesState, setProfilesState] = useState<ProfilesState | null>(null);
  const [form, setForm] = useState<ProfileFormState>(INITIAL_FORM);
  const [sessionEmail, setSessionEmail] = useState("demo@42lausanne.ch");
  const [errors, setErrors] = useState<FormErrors>({});
  const [loadingState, setLoadingState] = useState<"loading" | "ready" | "error">("loading");
  const [feedback, setFeedback] = useState<string | null>(null);
  const [feedbackTone, setFeedbackTone] = useState<"success" | "error">("success");
  const [isCreating, setIsCreating] = useState(false);
  const [switchingId, setSwitchingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadPage() {
      try {
        const [dashboard, profiles] = await Promise.all([getDashboardData(), listProfiles()]);
        if (cancelled) {
          return;
        }

        setSessionEmail(getMockSessionEmail() ?? "demo@42lausanne.ch");
        setTracks(dashboard.curriculum.tracks);
        setProfilesState(profiles);
        setForm((current) => ({
          ...current,
          track: current.track || dashboard.curriculum.tracks[0]?.id || "",
        }));
        setLoadingState("ready");
      } catch {
        if (!cancelled) {
          setLoadingState("error");
        }
      }
    }

    void loadPage();

    return () => {
      cancelled = true;
    };
  }, []);
  const activeProfile = profilesState?.activeProfile ?? null;

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
      setForm((current) => ({ ...current, login: "" }));
      setFeedbackTone("success");
      setFeedback(`Profile for ${formatTrackTitle(form.track, tracks)} is ready and now active.`);
    } catch (error) {
      setFeedbackTone("error");
      setFeedback(error instanceof Error ? error.message : "Unable to create a new profile.");
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
      setFeedbackTone("success");
      setFeedback(`${formatTrackTitle(profile.track, tracks)} is now the active profile.`);
    } catch (error) {
      setFeedbackTone("error");
      setFeedback(error instanceof Error ? error.message : "Unable to switch the active profile.");
    } finally {
      setSwitchingId(null);
    }
  }

  if (loadingState === "loading") {
    return (
      <main className="page-shell profiles-page">
        <section className="panel profiles-hero">
          <p className="eyebrow">Profiles</p>
          <h1>Loading profile workspace...</h1>
          <p className="lead">Preparing the available tracks and the current active learner context.</p>
        </section>
      </main>
    );
  }

  if (loadingState === "error" || profilesState === null) {
    return (
      <main className="page-shell profiles-page">
        <section className="panel profiles-hero">
          <p className="eyebrow">Profiles</p>
          <h1>Profile management is temporarily unavailable.</h1>
          <p className="lead">
            The UI could not load the profile catalog. Refresh the page or return to the dashboard.
          </p>
          <Link href="/" className="action-btn">
            Back to dashboard
          </Link>
        </section>
      </main>
    );
  }

  return (
    <main className="page-shell profiles-page">
      <section className="panel profiles-hero">
        <div className="profiles-hero-copy">
          <p className="eyebrow">Profiles</p>
          <h1>One account, several learner profiles, one active track at a time.</h1>
          <p className="lead">
            Use separate profiles to isolate progression across Shell, C and Python + AI while keeping a single
            authenticated account. The selected active profile becomes the learner context for the next steps.
          </p>
        </div>

        <div className="hero-grid profiles-metrics">
          <div className="metric-card">
            <span>Connected user</span>
            <strong>{sessionEmail}</strong>
          </div>
          <div className="metric-card">
            <span>Active profile</span>
            <strong>{activeProfile ? formatTrackTitle(activeProfile.track, tracks) : "None"}</strong>
          </div>
          <div className="metric-card">
            <span>Profiles linked</span>
            <strong>{profilesState.profiles.length}</strong>
          </div>
          <div className="metric-card">
            <span>Data source</span>
            <strong>{profilesState.mocked ? "Mocked web state" : "API live state"}</strong>
          </div>
        </div>
      </section>

      <section className="profiles-body">
        <article className="panel profiles-list-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Selection</p>
              <h2>Active learner context</h2>
            </div>
            <Link href="/" className="profiles-inline-link">
              Back to dashboard
            </Link>
          </div>

          <div className="profiles-card-grid">
            {profilesState.profiles.map((profile) => {
              const isActive = profile.id === profilesState.activeProfileId;

              return (
                <article
                  key={profile.id}
                  className={`profiles-card ${isActive ? "profiles-card--active" : ""}`}
                >
                  <div className="card-topline">
                    <span>{profile.track}</span>
                    <span>{isActive ? "Active" : "Inactive"}</span>
                  </div>
                  <h3>{formatTrackTitle(profile.track, tracks)}</h3>
                  <p className="muted">Login handle: {profile.login}</p>
                  <div className="profiles-meta">
                    <span>Started {formatDateLabel(profile.startedAt)}</span>
                    <span>{profile.currentModule ? `Current module: ${profile.currentModule}` : "No module selected yet"}</span>
                  </div>
                  <button
                    type="button"
                    className={`profiles-switch-btn ${isActive ? "profiles-switch-btn--active" : ""}`}
                    onClick={() => void handleSwitchProfile(profile)}
                    disabled={isActive || switchingId === profile.id}
                  >
                    {isActive ? "Active profile" : switchingId === profile.id ? "Switching..." : "Set active"}
                  </button>
                </article>
              );
            })}
          </div>
        </article>

        <aside className="panel profiles-create-panel">
          <div className="profiles-create-header">
            <p className="eyebrow">Creation</p>
            <h2>Add a track profile</h2>
            <p className="muted">
              One profile per track. Use the optional login field if you want a custom handle instead of the generated
              one.
            </p>
          </div>

          <form className="profiles-form" noValidate onSubmit={handleCreateProfile}>
            <label className="login-field">
              <span>Track</span>
              <select
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
              {errors.track && <small className="login-error">{errors.track}</small>}
            </label>

            <label className="login-field">
              <span>Custom login handle (optional)</span>
              <input
                type="text"
                name="login"
                placeholder="learner-shell"
                value={form.login}
                onChange={(event) => updateField("login", event.target.value)}
                aria-invalid={Boolean(errors.login)}
              />
              {errors.login && <small className="login-error">{errors.login}</small>}
            </label>

            <button type="submit" className="action-btn" disabled={isCreating}>
              {isCreating ? "Creating profile..." : "Create profile"}
            </button>
          </form>

          {feedback && (
            <div
              className={`login-feedback ${
                feedbackTone === "success" ? "login-feedback--success" : "login-feedback--error"
              }`}
              aria-live="polite"
            >
              {feedback}
            </div>
          )}

          <div className="profiles-note">
            <strong>Current integration state</strong>
            <p className="muted">
              The page calls the real `/api/v1/profiles` endpoints when a bearer token is available. Otherwise it keeps
              the same UX using mocked browser state so frontend work can progress independently.
            </p>
          </div>
        </aside>
      </section>
    </main>
  );
}
