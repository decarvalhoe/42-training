"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type ThemeName = "hacker-hud" | "warm-classic";
type ContrastMode = "default" | "high";
type DensityMode = "comfortable" | "compact";
type MotionMode = "system" | "reduce";

type UiPreferencesValue = {
  theme: ThemeName;
  contrast: ContrastMode;
  density: DensityMode;
  motion: MotionMode;
  setTheme: (value: ThemeName) => void;
  setContrast: (value: ContrastMode) => void;
  setDensity: (value: DensityMode) => void;
  setMotion: (value: MotionMode) => void;
};

const STORAGE_KEY = "ui-preferences";

const DEFAULT_PREFERENCES = {
  theme: "hacker-hud" as ThemeName,
  contrast: "default" as ContrastMode,
  density: "comfortable" as DensityMode,
  motion: "system" as MotionMode,
};

const UiPreferencesContext = createContext<UiPreferencesValue | null>(null);

function applyPreferencesToDocument({
  theme,
  contrast,
  density,
  motion,
}: typeof DEFAULT_PREFERENCES) {
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.dataset.contrast = contrast;
  root.dataset.density = density;
  root.dataset.motion = motion;
}

function readStoredPreferences() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw === null) {
      return DEFAULT_PREFERENCES;
    }

    const parsed = JSON.parse(raw) as Partial<typeof DEFAULT_PREFERENCES>;
    return {
      theme: parsed.theme ?? DEFAULT_PREFERENCES.theme,
      contrast: parsed.contrast ?? DEFAULT_PREFERENCES.contrast,
      density: parsed.density ?? DEFAULT_PREFERENCES.density,
      motion: parsed.motion ?? DEFAULT_PREFERENCES.motion,
    };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function UiPreferencesProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<ThemeName>(DEFAULT_PREFERENCES.theme);
  const [contrast, setContrast] = useState<ContrastMode>(DEFAULT_PREFERENCES.contrast);
  const [density, setDensity] = useState<DensityMode>(DEFAULT_PREFERENCES.density);
  const [motion, setMotion] = useState<MotionMode>(DEFAULT_PREFERENCES.motion);

  useEffect(() => {
    const stored = readStoredPreferences();
    setTheme(stored.theme);
    setContrast(stored.contrast);
    setDensity(stored.density);
    setMotion(stored.motion);
    applyPreferencesToDocument(stored);
  }, []);

  useEffect(() => {
    const value = { theme, contrast, density, motion };
    applyPreferencesToDocument(value);
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  }, [contrast, density, motion, theme]);

  return (
    <UiPreferencesContext.Provider
      value={{
        theme,
        contrast,
        density,
        motion,
        setTheme,
        setContrast,
        setDensity,
        setMotion,
      }}
    >
      {children}
    </UiPreferencesContext.Provider>
  );
}

export function useUiPreferences() {
  const context = useContext(UiPreferencesContext);
  if (context === null) {
    throw new Error("useUiPreferences must be used within UiPreferencesProvider");
  }

  return context;
}
