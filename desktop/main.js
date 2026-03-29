/**
 * Electron main process for 42 Training desktop shell.
 *
 * Lifecycle:
 *   1. Spawn the Next.js standalone server from extraResources.
 *   2. Wait for the health-check endpoint to respond.
 *   3. Open a BrowserWindow pointing at the local server.
 *   4. On quit, tear down the child process.
 *
 * The Python backend services (API + AI Gateway) are expected to run
 * independently — either via Docker Desktop or manually.
 * Set NEXT_PUBLIC_API_URL and NEXT_PUBLIC_AI_GATEWAY_URL env vars to
 * point the frontend at the running backends.
 */

const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");

const WEB_PORT = Number(process.env.PORT) || 3042;
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let mainWindow = null;
let serverProcess = null;

/* ------------------------------------------------------------------ */
/*  Next.js server management                                          */
/* ------------------------------------------------------------------ */

function getServerPath() {
  const resourcesPath = process.resourcesPath || path.join(__dirname, "..");
  return path.join(resourcesPath, "web", "apps", "web", "server.js");
}

function startServer() {
  const serverPath = getServerPath();

  serverProcess = spawn(process.execPath.includes("electron") ? "node" : process.execPath, [serverPath], {
    env: {
      ...process.env,
      PORT: String(WEB_PORT),
      HOSTNAME: "127.0.0.1",
      NEXT_PUBLIC_API_URL: API_URL,
      NEXT_PUBLIC_AI_GATEWAY_URL: process.env.NEXT_PUBLIC_AI_GATEWAY_URL || "http://localhost:8100",
      NODE_ENV: "production",
    },
    stdio: "pipe",
  });

  serverProcess.stdout?.on("data", (data) => {
    console.log(`[next] ${data.toString().trim()}`);
  });

  serverProcess.stderr?.on("data", (data) => {
    console.error(`[next] ${data.toString().trim()}`);
  });

  serverProcess.on("error", (err) => {
    console.error("Failed to start Next.js server:", err.message);
    dialog.showErrorBox(
      "Server Error",
      `Could not start the web server.\n\n${err.message}\n\nMake sure the application was built correctly.`
    );
  });

  serverProcess.on("exit", (code) => {
    console.log(`Next.js server exited with code ${code}`);
    serverProcess = null;
  });
}

function stopServer() {
  if (serverProcess) {
    serverProcess.kill();
    serverProcess = null;
  }
}

/* ------------------------------------------------------------------ */
/*  Health check                                                       */
/* ------------------------------------------------------------------ */

function waitForServer(url, retries = 30, interval = 500) {
  return new Promise((resolve, reject) => {
    let attempts = 0;

    function check() {
      attempts += 1;
      http
        .get(url, (res) => {
          if (res.statusCode === 200 || res.statusCode === 307) {
            resolve();
          } else if (attempts < retries) {
            setTimeout(check, interval);
          } else {
            reject(new Error(`Server not ready after ${retries} attempts (last status: ${res.statusCode})`));
          }
        })
        .on("error", () => {
          if (attempts < retries) {
            setTimeout(check, interval);
          } else {
            reject(new Error(`Server not reachable after ${retries} attempts`));
          }
        });
    }

    check();
  });
}

/* ------------------------------------------------------------------ */
/*  Window                                                             */
/* ------------------------------------------------------------------ */

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    title: "42 Training",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL(`http://127.0.0.1:${WEB_PORT}`);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

/* ------------------------------------------------------------------ */
/*  App lifecycle                                                      */
/* ------------------------------------------------------------------ */

app.on("ready", async () => {
  startServer();

  try {
    await waitForServer(`http://127.0.0.1:${WEB_PORT}/health`);
  } catch {
    // Fallback: try loading anyway — the page may still serve
    console.warn("Health check failed, loading frontend anyway");
  }

  createWindow();
});

app.on("window-all-closed", () => {
  stopServer();
  app.quit();
});

app.on("before-quit", () => {
  stopServer();
});
