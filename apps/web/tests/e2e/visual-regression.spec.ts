import { expect, test, type Page } from "@playwright/test";

const VISUAL_SESSION = {
  user: {
    id: "visual-user",
    email: "visual@42-training.local",
    status: "active",
  },
  learner_profile: {
    id: "visual-profile",
    login: "visual-shell",
    track: "shell",
    current_module: "shell-basics",
  },
  profiles: [
    {
      id: "visual-profile",
      login: "visual-shell",
      track: "shell",
      current_module: "shell-basics",
    },
  ],
};
const VISUAL_WEB_URL = process.env.VISUAL_TEST_BASE_URL ?? "http://127.0.0.1:3001";
const AUTH_COOKIE_NAME = "training_session";
const VISUAL_SESSION_COOKIE_NAME = "training_visual_session";
const VISUAL_AUTH_STORAGE = {
  user: {
    id: "visual-user",
    email: "visual@42-training.local",
    status: "active",
  },
  learnerProfile: {
    id: "visual-profile",
    login: "visual-shell",
    track: "shell",
    current_module: "shell-basics",
  },
  profiles: [
    {
      id: "visual-profile",
      login: "visual-shell",
      track: "shell",
      current_module: "shell-basics",
    },
  ],
};

async function mockAuthenticatedSession(page: Page) {
  await page.context().addCookies([
    {
      name: AUTH_COOKIE_NAME,
      value: "visual-test-session",
      url: VISUAL_WEB_URL,
      httpOnly: false,
      secure: false,
      sameSite: "Lax",
    },
    {
      name: VISUAL_SESSION_COOKIE_NAME,
      value: "1",
      url: VISUAL_WEB_URL,
      httpOnly: false,
      secure: false,
      sameSite: "Lax",
    },
  ]);

  await page.addInitScript((session) => {
    (window as Window & { __TRAINING_VISUAL_AUTH__?: unknown }).__TRAINING_VISUAL_AUTH__ = session;
    window.localStorage.setItem("training-auth-session", JSON.stringify(session));
  }, VISUAL_AUTH_STORAGE);

  await page.route("**/api/v1/auth/me", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(VISUAL_SESSION),
    });
  });
}

async function prepareSurface(page: Page, route: string, options?: { authenticated?: boolean }) {
  if (options?.authenticated) {
    await mockAuthenticatedSession(page);
  }

  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(route);

  if (options?.authenticated) {
    await page.locator("#main-content").waitFor({ state: "visible" });
    return page;
  }

  await page.locator("form.login-form").waitFor({ state: "visible" });
  return page;
}

async function expectStableScreenshot(page: Page, snapshotName: string) {
  await expect(page).toHaveScreenshot(snapshotName, {
    maxDiffPixels: 500,
  });
}

test("login surface stays visually aligned", async ({ page }) => {
  const surface = await prepareSurface(page, "/login");
  await expectStableScreenshot(surface, "login-surface.png");
});

test("learner home stays visually aligned", async ({ page }) => {
  const surface = await prepareSurface(page, "/", { authenticated: true });
  await expectStableScreenshot(surface, "learner-home-surface.png");
});

test("skill graph stays visually aligned", async ({ page }) => {
  const surface = await prepareSurface(page, "/dashboard", { authenticated: true });
  await expectStableScreenshot(surface, "skill-graph-surface.png");
});

test("defense setup stays visually aligned", async ({ page }) => {
  const surface = await prepareSurface(page, "/defense", { authenticated: true });
  await expectStableScreenshot(surface, "defense-setup-surface.png");
});

test("mentor workspace stays visually aligned", async ({ page }) => {
  const surface = await prepareSurface(page, "/mentor", { authenticated: true });
  await expectStableScreenshot(surface, "mentor-workspace-surface.png");
});
