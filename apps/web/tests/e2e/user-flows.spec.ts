import { expect, test } from "@playwright/test";

function uniqueId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

test("redirects unauthenticated users and surfaces invalid login", async ({ page }) => {
  await page.goto("/profiles");

  await expect(page).toHaveURL(/\/login\?next=%2Fprofiles/);

  const form = page.locator("form.login-form");
  await form.getByLabel("Email").fill("missing-user@example.com");
  await form.getByLabel("Password").fill("wrongpass");
  await form.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByText("Invalid email or password")).toBeVisible();
});

test("registers, creates a profile, visits a module, and submits a review", async ({ page }) => {
  const suffix = uniqueId();
  const email = `playwright-${suffix}@example.com`;
  const reviewerId = `reviewer-${suffix}`;
  const loginHandle = `shell-${suffix}`;

  await page.goto("/login");

  await page.getByRole("button", { name: "Create account", exact: true }).first().click();

  const loginForm = page.locator("form.login-form");
  await loginForm.getByLabel("Email").fill(email);
  await loginForm.getByLabel("Password").fill("supersecret");
  await loginForm.getByRole("button", { name: "Create account", exact: true }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: /One learning system/i })).toBeVisible();
  await expect(page.getByText(email)).toBeVisible();

  await page.goto("/profiles");
  await expect(page.getByRole("heading", { name: "Add a track profile" })).toBeVisible();

  const profilesForm = page.locator("form.profiles-form");
  await profilesForm.getByLabel("Track").selectOption("shell");
  await profilesForm.getByLabel("Custom login handle (optional)").fill(loginHandle);
  await profilesForm.getByRole("button", { name: "Create profile" }).click();

  await expect(page.getByText(/Profile for .* is ready and now active\./)).toBeVisible();
  await expect(page.getByText(`Login handle: ${loginHandle}`)).toBeVisible();

  await page.goto("/modules/shell-basics");
  await expect(page.getByRole("heading", { name: "Navigation" })).toBeVisible();
  await expect(page.getByRole("button", { name: /Start module|Continue|Review module/ })).toBeVisible();

  await page.goto("/review");
  await expect(page.getByRole("heading", { name: "Submit a guided review" })).toBeVisible();

  const reviewForm = page.locator("form.review-form");
  await reviewForm.getByLabel("Module").selectOption("shell-basics");
  await reviewForm.getByLabel("Reviewer ID").fill(reviewerId);
  await reviewForm.getByLabel("Code or command snippet").fill("pwd\nls -la\ncd ..");
  await reviewForm
    .getByLabel("Review notes")
    .fill("Need a clearer explanation of hidden files and the reason for each command in the sequence.");
  await reviewForm
    .getByLabel("Evidence notes")
    .fill("Captured terminal output\nNeed to explain why hidden files matter");
  await reviewForm.getByRole("button", { name: "Submit review" }).click();

  await expect(page.getByText(/Review submitted for /)).toBeVisible();
  await expect(page.getByText(reviewerId)).toBeVisible();
  await expect(
    page.getByText("Need a clearer explanation of hidden files and the reason for each command in the sequence."),
  ).toBeVisible();
});
