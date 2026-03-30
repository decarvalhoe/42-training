import { defineConfig, devices } from "@playwright/test";

const webPort = Number(process.env.VISUAL_WEB_PORT ?? 3001);
const webHost = process.env.VISUAL_WEB_HOST ?? "127.0.0.1";
const baseURL = `http://${webHost}:${webPort}`;

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: /visual-regression\.spec\.ts/,
  fullyParallel: false,
  timeout: 60_000,
  expect: {
    timeout: 10_000,
    toHaveScreenshot: {
      animations: "disabled",
      caret: "hide",
      maxDiffPixels: 500,
      scale: "css",
    },
  },
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"]],
  use: {
    ...devices["Desktop Chrome"],
    viewport: { width: 1440, height: 1024 },
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    colorScheme: "dark",
  },
  webServer: {
    command: `bash -lc 'cd ${__dirname} && NEXT_PUBLIC_ENABLE_DEMO_MODE=true NEXT_PUBLIC_API_URL=http://127.0.0.1:65530 NEXT_PUBLIC_ENABLE_E2E_API_OVERRIDE=false NEXT_PUBLIC_ENABLE_VISUAL_TEST_SESSION=true npm run dev -- --webpack --hostname ${webHost} --port ${webPort}'`,
    url: baseURL,
    reuseExistingServer: !process.env.CI,
    timeout: 300_000,
  },
});
