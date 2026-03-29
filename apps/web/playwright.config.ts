import path from "node:path";

import { defineConfig } from "@playwright/test";

const repoRoot = path.resolve(__dirname, "../..");
const apiPort = Number(process.env.E2E_API_PORT ?? 8000);
const webPort = Number(process.env.E2E_WEB_PORT ?? 3000);
const webHost = process.env.E2E_WEB_HOST ?? "127.0.0.1";
const baseURL = `http://${webHost}:${webPort}`;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: [
    {
      command: `bash -lc 'cd ${repoRoot} && API_PORT=${apiPort} API_E2E_DB_PATH=${path.join(
        repoRoot,
        ".tmp",
        "playwright",
        "api.sqlite3",
      )} DATA_ROOT=${repoRoot} CORS_ALLOW_ORIGINS=${baseURL},http://localhost:${webPort} ./scripts/start_api_e2e.sh'`,
      url: `http://127.0.0.1:${apiPort}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `bash -lc 'cd ${__dirname} && NEXT_PUBLIC_API_URL=http://127.0.0.1:${apiPort} NEXT_PUBLIC_ENABLE_DEMO_MODE=false npm run dev -- --hostname ${webHost} --port ${webPort}'`,
      url: baseURL,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
