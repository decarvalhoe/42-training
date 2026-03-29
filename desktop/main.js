/**
 * 42-Training — Electron main process.
 *
 * Lifecycle:
 *   1. Spawn the Python API backend (port 8000) with SQLite
 *   2. Spawn the Python AI Gateway (port 8100)
 *   3. Spawn the Next.js frontend (port 3000)
 *   4. Wait for all health checks
 *   5. Open the BrowserWindow
 *   6. On quit, tear down all child processes
 */

const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const http = require("http");

/* ------------------------------------------------------------------ */
/*  Paths                                                              */
/* ------------------------------------------------------------------ */

const IS_PACKAGED = app.isPackaged;
const RESOURCES = IS_PACKAGED
  ? path.join(process.resourcesPath)
  : path.join(__dirname);

const BACKEND_DIR = path.join(RESOURCES, "backend");
const DATA_DIR = path.join(RESOURCES, "data");
const FRONTEND_DIR = path.join(RESOURCES, "frontend");

const API_DIR = path.join(BACKEND_DIR, "api");
const GATEWAY_DIR = path.join(BACKEND_DIR, "ai_gateway");
const VENV_PYTHON_API = path.join(API_DIR, "venv", "bin", "python");
const VENV_PYTHON_GW = path.join(GATEWAY_DIR, "venv", "bin", "python");

/* ------------------------------------------------------------------ */
/*  Ports                                                              */
/* ------------------------------------------------------------------ */

const API_PORT = 8000;
const GATEWAY_PORT = 8100;
const WEB_PORT = 3000;

/* ------------------------------------------------------------------ */
/*  State                                                              */
/* ------------------------------------------------------------------ */

const children = [];
let mainWindow = null;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function userDataPath(filename) {
  return path.join(app.getPath("userData"), filename);
}

function healthCheck(port, pathname, retries = 40, intervalMs = 500) {
  return new Promise((resolve, reject) => {
    let attempt = 0;
    const check = () => {
      const req = http.get(
        { hostname: "127.0.0.1", port, path: pathname, timeout: 2000 },
        (res) => {
          if (res.statusCode === 200) return resolve();
          retry();
        },
      );
      req.on("error", retry);
      req.on("timeout", () => {
        req.destroy();
        retry();
      });
    };
    const retry = () => {
      if (++attempt >= retries) {
        return reject(new Error(`Service on port ${port} did not start after ${retries} attempts`));
      }
      setTimeout(check, intervalMs);
    };
    check();
  });
}

function spawnService(label, command, args, cwd, env) {
  const proc = spawn(command, args, {
    cwd,
    env: { ...process.env, ...env },
    stdio: ["ignore", "pipe", "pipe"],
  });
  children.push(proc);

  proc.stdout.on("data", (d) => console.log(`[${label}] ${d.toString().trim()}`));
  proc.stderr.on("data", (d) => console.error(`[${label}] ${d.toString().trim()}`));
  proc.on("error", (err) => console.error(`[${label}] failed to start:`, err.message));

  return proc;
}

function killAll() {
  for (const proc of children) {
    if (!proc.killed) {
      proc.kill("SIGTERM");
      setTimeout(() => {
        if (!proc.killed) proc.kill("SIGKILL");
      }, 3000);
    }
  }
}

/* ------------------------------------------------------------------ */
/*  Service launchers                                                  */
/* ------------------------------------------------------------------ */

function startApi() {
  const dbPath = userDataPath("42training.db");
  const dbUrl = `sqlite+aiosqlite:///${dbPath}`;

  return spawnService(
    "api",
    VENV_PYTHON_API,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(API_PORT)],
    API_DIR,
    {
      DATABASE_URL: dbUrl,
      APP_SECRET_KEY: "desktop-local-key",
      CURRICULUM_PATH: path.join(DATA_DIR, "42_lausanne_curriculum.json"),
      PROGRESSION_PATH: path.join(DATA_DIR, "progression.json"),
    },
  );
}

function startGateway() {
  return spawnService(
    "ai_gateway",
    VENV_PYTHON_GW,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(GATEWAY_PORT)],
    GATEWAY_DIR,
    {
      AI_GATEWAY_API_BASE_URL: `http://127.0.0.1:${API_PORT}`,
      CURRICULUM_PATH: path.join(DATA_DIR, "42_lausanne_curriculum.json"),
      PROGRESSION_PATH: path.join(DATA_DIR, "progression.json"),
    },
  );
}

function startFrontend() {
  const nodeBin = process.execPath.includes("Electron")
    ? "node"
    : process.execPath;

  return spawnService(
    "web",
    nodeBin,
    ["node_modules/next/dist/bin/next", "start", "--port", String(WEB_PORT)],
    FRONTEND_DIR,
    {
      NEXT_PUBLIC_API_URL: `http://127.0.0.1:${API_PORT}`,
      NEXT_PUBLIC_AI_GATEWAY_URL: `http://127.0.0.1:${GATEWAY_PORT}`,
      PORT: String(WEB_PORT),
    },
  );
}

/* ------------------------------------------------------------------ */
/*  Window                                                             */
/* ------------------------------------------------------------------ */

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    title: "42-Training",
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
  try {
    startApi();
    startGateway();

    await healthCheck(API_PORT, "/health");
    console.log("[boot] API is ready");

    await healthCheck(GATEWAY_PORT, "/health");
    console.log("[boot] AI Gateway is ready");

    startFrontend();
    await healthCheck(WEB_PORT, "/");
    console.log("[boot] Frontend is ready");

    createWindow();
  } catch (err) {
    dialog.showErrorBox(
      "42-Training — Startup Error",
      `A service failed to start:\n\n${err.message}\n\nCheck Console.app for details.`,
    );
    killAll();
    app.quit();
  }
});

app.on("window-all-closed", () => {
  killAll();
  app.quit();
});

app.on("before-quit", killAll);
