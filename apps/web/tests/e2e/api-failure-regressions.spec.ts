import { expect, test, type Page, type Route } from "@playwright/test";

const WEB_URL = "http://127.0.0.1:3000";
const API_URL = "http://127.0.0.1:8000";
const DEAD_API_URL = "http://127.0.0.1:65530";
const PASSWORD = "supersecret";
const API_OVERRIDE_COOKIE_KEY = "training_api_base_override";
const DEMO_MODE_COOKIE_KEY = "training_demo_mode";

function uniqueId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

async function registerAuthenticatedSession(page: Page) {
  const email = `api-failure-${uniqueId()}@example.com`;
  const response = await page.context().request.post(`${API_URL}/api/v1/auth/register`, {
    data: {
      email,
      password: PASSWORD,
    },
  });

  expect(response.ok()).toBeTruthy();
  return email;
}

async function addAppCookies(page: Page, values: Record<string, string>) {
  await page.context().addCookies(
    Object.entries(values).map(([name, value]) => ({
      name,
      value,
      url: WEB_URL,
    })),
  );
}

async function fulfillOutage(route: Route) {
  await route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ detail: "service unavailable" }),
  });
}

test("dashboard, analytics and defense stop loudly when the live API is unavailable", async ({ page }) => {
  await registerAuthenticatedSession(page);
  await addAppCookies(page, {
    [API_OVERRIDE_COOKIE_KEY]: DEAD_API_URL,
  });

  for (const path of ["/", "/analytics", "/defense"]) {
    await page.goto(path);
    await expect(page.getByText(/stopped instead of/i)).toBeVisible();
    await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  }
});

test("dashboard, analytics and defense expose demo mode explicitly when fallback is opt-in", async ({ page }) => {
  await registerAuthenticatedSession(page);
  await addAppCookies(page, {
    [API_OVERRIDE_COOKIE_KEY]: DEAD_API_URL,
    [DEMO_MODE_COOKIE_KEY]: "true",
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: /One learning system/i })).toBeVisible();
  await expect(page.getByText("Demo mode")).toBeVisible();

  await page.goto("/analytics");
  await expect(page.getByRole("heading", { name: "Analytics dashboard" })).toBeVisible();
  await expect(page.getByText("Demo mode")).toBeVisible();

  await page.goto("/defense");
  await expect(page.getByRole("heading", { name: "Defense and guided review" })).toBeVisible();
  await expect(page.getByText("Demo mode")).toBeVisible();
});

test("profiles, review and defense keep explicit error and retry states during API outages", async ({ page }) => {
  await registerAuthenticatedSession(page);

  await page.route("**/api/v1/profiles**", fulfillOutage);
  await page.goto("/profiles");
  await expect(page.getByRole("heading", { name: "Profile management is temporarily unavailable." })).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  await page.unroute("**/api/v1/profiles**", fulfillOutage);

  await page.route("**/api/v1/review-attempts**", fulfillOutage);
  await page.goto("/review");
  await expect(page.getByRole("heading", { name: "Review workspace unavailable" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  await page.unroute("**/api/v1/review-attempts**", fulfillOutage);

  await page.route("**/api/v1/defense/start", fulfillOutage);
  await page.goto("/defense");
  await expect(page.getByRole("heading", { name: "Start a defense session" })).toBeVisible();
  await page.getByRole("button", { name: "Begin defense" }).click();
  await expect(page.getByText("service unavailable")).toBeVisible();
});
