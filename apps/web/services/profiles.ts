import { getStoredAccessToken, getStoredSessionEmail } from "@/services/auth";

export type ProfileItem = {
  id: string;
  login: string;
  track: string;
  currentModule: string | null;
  startedAt: string;
  updatedAt: string;
};

export type ProfilesState = {
  activeProfileId: string | null;
  activeProfile: ProfileItem | null;
  profiles: ProfileItem[];
  mocked: boolean;
};

export type CreateProfilePayload = {
  track: string;
  login?: string;
};

type ApiProfile = {
  id: string;
  login: string;
  track: string;
  current_module?: string | null;
  started_at?: string;
  updated_at?: string;
};

type ApiProfilesResponse = {
  active_profile_id: string | null;
  active_profile: ApiProfile | null;
  profiles: ApiProfile[];
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const FALLBACK_SESSION_EMAIL = "demo@42lausanne.ch";

function nowIso() {
  return new Date().toISOString();
}

function profileStorageKey(email: string) {
  return `training-mock-profiles:${email}`;
}

function normalizeLoginCandidate(value: string) {
  return value.trim().toLowerCase().replace(/[^a-z0-9-]+/g, "-").replace(/-{2,}/g, "-").replace(/^-|-$/g, "");
}

function makeProfileId(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function mapApiProfile(profile: ApiProfile): ProfileItem {
  return {
    id: profile.id,
    login: profile.login,
    track: profile.track,
    currentModule: profile.current_module ?? null,
    startedAt: profile.started_at ?? nowIso(),
    updatedAt: profile.updated_at ?? nowIso(),
  };
}

function mapApiProfilesState(data: ApiProfilesResponse, mocked: boolean): ProfilesState {
  const profiles = data.profiles.map(mapApiProfile);
  const activeProfile =
    (data.active_profile ? mapApiProfile(data.active_profile) : null) ??
    profiles.find((profile) => profile.id === data.active_profile_id) ??
    null;

  return {
    activeProfileId: data.active_profile_id,
    activeProfile,
    profiles,
    mocked,
  };
}

function getSessionEmail() {
  return getStoredSessionEmail() ?? FALLBACK_SESSION_EMAIL;
}

function seedMockProfiles(email: string): ProfilesState {
  const timestamp = nowIso();
  const loginBase = normalizeLoginCandidate(email.split("@", 1)[0]) || "learner";
  const shellProfile: ProfileItem = {
    id: makeProfileId("profile"),
    login: `${loginBase}-shell`,
    track: "shell",
    currentModule: "shell-basics",
    startedAt: timestamp,
    updatedAt: timestamp,
  };

  return {
    activeProfileId: shellProfile.id,
    activeProfile: shellProfile,
    profiles: [shellProfile],
    mocked: true,
  };
}

function readMockProfiles(): ProfilesState {
  if (typeof window === "undefined") {
    return seedMockProfiles(FALLBACK_SESSION_EMAIL);
  }

  const email = getSessionEmail();
  const stored = window.localStorage.getItem(profileStorageKey(email));
  if (!stored) {
    const seeded = seedMockProfiles(email);
    writeMockProfiles(seeded, email);
    return seeded;
  }

  try {
    const parsed = JSON.parse(stored) as ProfilesState;
    const activeProfile =
      parsed.profiles.find((profile) => profile.id === parsed.activeProfileId) ?? parsed.activeProfile ?? null;
    return { ...parsed, activeProfile, mocked: true };
  } catch {
    const seeded = seedMockProfiles(email);
    writeMockProfiles(seeded, email);
    return seeded;
  }
}

function writeMockProfiles(state: ProfilesState, email = getSessionEmail()) {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(profileStorageKey(email), JSON.stringify({ ...state, mocked: true }));
}

async function apiRequest(path: string, init?: RequestInit) {
  const token = getStoredAccessToken();
  if (!token) {
    throw new Error("No bearer token available");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    throw new Error(`Profiles API returned ${response.status}`);
  }

  return response.json() as Promise<ApiProfilesResponse>;
}

export async function listProfiles(): Promise<ProfilesState> {
  try {
    return mapApiProfilesState(await apiRequest("/api/v1/profiles"), false);
  } catch {
    return readMockProfiles();
  }
}

export async function createProfile(payload: CreateProfilePayload): Promise<ProfilesState> {
  try {
    const data = await apiRequest("/api/v1/profiles", {
      method: "POST",
      body: JSON.stringify({ track: payload.track, login: payload.login || undefined }),
    });
    return mapApiProfilesState(data, false);
  } catch {
    const current = readMockProfiles();
    if (current.profiles.some((profile) => profile.track === payload.track)) {
      throw new Error(`A profile for track "${payload.track}" already exists.`);
    }

    const timestamp = nowIso();
    const email = getSessionEmail();
    const loginBase = normalizeLoginCandidate(email.split("@", 1)[0]) || "learner";
    const login = payload.login?.trim()
      ? normalizeLoginCandidate(payload.login)
      : normalizeLoginCandidate(`${loginBase}-${payload.track.replace(/_/g, "-")}`);

    if (!login) {
      throw new Error("Profile login is required.");
    }

    const profile: ProfileItem = {
      id: makeProfileId("profile"),
      login,
      track: payload.track,
      currentModule: null,
      startedAt: timestamp,
      updatedAt: timestamp,
    };
    const next: ProfilesState = {
      activeProfileId: profile.id,
      activeProfile: profile,
      profiles: [...current.profiles, profile],
      mocked: true,
    };
    writeMockProfiles(next, email);
    return next;
  }
}

export async function switchActiveProfile(profileId: string): Promise<ProfilesState> {
  try {
    const data = await apiRequest(`/api/v1/profiles/${profileId}/switch`, { method: "POST" });
    return mapApiProfilesState(data, false);
  } catch {
    const current = readMockProfiles();
    const activeProfile = current.profiles.find((profile) => profile.id === profileId);
    if (!activeProfile) {
      throw new Error("Profile not found.");
    }

    const next = {
      ...current,
      activeProfileId: activeProfile.id,
      activeProfile,
      mocked: true,
    };
    writeMockProfiles(next);
    return next;
  }
}
