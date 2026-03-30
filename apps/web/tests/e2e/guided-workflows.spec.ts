import { expect, test } from "@playwright/test";

const API_URL = "http://127.0.0.1:8000";
const PASSWORD = "supersecret";

function uniqueId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

async function registerAuthenticatedSession(page: import("@playwright/test").Page) {
  const email = `workflow-${uniqueId()}@example.com`;
  const response = await page.context().request.post(`${API_URL}/api/v1/auth/register`, {
    data: {
      email,
      password: PASSWORD,
    },
  });

  expect(response.ok()).toBeTruthy();
}

test("guided workflow surfaces expose their canonical headings", async ({ page }) => {
  await registerAuthenticatedSession(page);

  await page.goto("/mentor");
  await expect(page.locator("#main-content").getByText(/AI mentor \/\//i)).toBeVisible();

  await page.goto("/evidence");
  await expect(page.getByRole("heading", { name: "Linked artifacts" })).toBeVisible();

  await page.goto("/sessions");
  await expect(page.getByRole("heading", { name: "Tmux runtime" })).toBeVisible();

  await page.goto("/analytics");
  await expect(page.getByRole("heading", { name: "Analytics dashboard" })).toBeVisible();
});
