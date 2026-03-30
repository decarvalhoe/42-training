/**
 * 42-Training — Electron main process.
 *
 * Desktop runtime modes:
 *   - Full bundle mode: packaged frontend + bundled Python API/AI Gateway
 *   - Frontend-only mode: packaged frontend + external backends on 8000/8100
 *
 * The runtime auto-detects bundled backends. This keeps the macOS desktop
 * bundle self-contained while allowing the Windows executables to ship only
 * the frontend shell and reuse external services.
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
const RESOURCES = IS_PACKAGED ? process.resourcesPath : path.join(__dirname);
const DEV_FRONTEND_DIR = path.join(__dirname, "..", "apps", "web", ".next", "standalone");
const API_DIR = path.join(RESOURCES, "backend", "api");
const GATEWAY_DIR = path.join(RESOURCES, "backend", "ai_gateway");

/* ------------------------------------------------------------------ */
/*  Ports                                                              */
/* ------------------------------------------------------------------ */

const API_PORT = 8000;
const GATEWAY_PORT = 8100;
const WEB_PORT = Number(process.env.PORT) || (hasBundledBackends() ? 3000 : 3042);

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

function logPath() {
  return userDataPath("desktop.log");
}

function appendLog(message) {
  const line = `[${new Date().toISOString()}] ${message}\n`;
  try {
    fs.appendFileSync(logPath(), line);
  } catch (error) {
    console.error("[log] failed to write log file:", error.message);
  }
}

function fileExists(targetPath) {
  try {
    return fs.existsSync(targetPath);
  } catch {
    return false;
  }
}

function resolvePythonExecutable(serviceDir) {
  const candidates = [
    path.join(serviceDir, "venv", "Scripts", "python.exe"),
    path.join(serviceDir, "venv", "bin", "python"),
  ];
  return candidates.find(fileExists) || null;
}

function hasBundledBackends() {
  return Boolean(resolvePythonExecutable(API_DIR) && resolvePythonExecutable(GATEWAY_DIR));
}

function resolveFrontendDir() {
  const candidates = IS_PACKAGED
    ? [path.join(RESOURCES, "frontend"), path.join(RESOURCES, "web")]
    : [DEV_FRONTEND_DIR, path.join(__dirname, "frontend")];

  return candidates.find((candidate) => fileExists(path.join(candidate, "server.js"))) || null;
}

function healthCheck(port, pathname, retries = 40, intervalMs = 500, acceptableStatusCodes = [200]) {
  return new Promise((resolve, reject) => {
    let attempt = 0;
    const allowed = new Set(acceptableStatusCodes);

    const check = () => {
      const req = http.get(
        { hostname: "127.0.0.1", port, path: pathname, timeout: 2000 },
        (res) => {
          if (allowed.has(res.statusCode)) {
            return resolve();
          }
          retry(`status ${res.statusCode}`);
        },
      );

      req.on("error", (error) => retry(error.message));
      req.on("timeout", () => {
        req.destroy();
        retry("timeout");
      });
    };

    const retry = (reason) => {
      attempt += 1;
      if (attempt >= retries) {
        return reject(
          new Error(`Service on port ${port} did not start after ${retries} attempts (${reason})`),
        );
      }
      setTimeout(check, intervalMs);
    };

    check();
  });
}

function spawnService(label, command, args, cwd, env) {
  appendLog(`[${label}] spawn ${command} ${args.join(" ")} (cwd=${cwd})`);

  const proc = spawn(command, args, {
    cwd,
    env: { ...process.env, ...env },
    stdio: ["ignore", "pipe", "pipe"],
  });

  children.push(proc);

  proc.stdout.on("data", (chunk) => {
    const message = chunk.toString().trim();
    if (message) {
      console.log(`[${label}] ${message}`);
      appendLog(`[${label}] ${message}`);
    }
  });

  proc.stderr.on("data", (chunk) => {
    const message = chunk.toString().trim();
    if (message) {
      console.error(`[${label}] ${message}`);
      appendLog(`[${label}] ${message}`);
    }
  });

  proc.on("error", (error) => {
    console.error(`[${label}] failed to start:`, error.message);
    appendLog(`[${label}] failed to start: ${error.message}`);
  });

  proc.on("exit", (code, signal) => {
    appendLog(`[${label}] exited with code=${code} signal=${signal}`);
  });

  return proc;
}

function killAll() {
  for (const proc of children) {
    if (!proc.killed) {
      proc.kill("SIGTERM");
      setTimeout(() => {
        if (!proc.killed) {
          proc.kill("SIGKILL");
        }
      }, 3000);
    }
  }
}

function startBundledApi() {
  const python = resolvePythonExecutable(API_DIR);
  if (!python) {
    throw new Error("Bundled API runtime not found");
  }

  const dbPath = userDataPath("42training.db");
  const dbUrl = `sqlite+aiosqlite:///${dbPath}`;

  return spawnService(
    "api",
    python,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(API_PORT)],
    API_DIR,
    {
      DATABASE_URL: dbUrl,
      APP_SECRET_KEY: "desktop-local-key",
      CURRICULUM_PATH: path.join(RESOURCES, "data", "42_lausanne_curriculum.json"),
      PROGRESSION_PATH: path.join(RESOURCES, "data", "progression.json"),
    },
  );
}

function startBundledGateway() {
  const python = resolvePythonExecutable(GATEWAY_DIR);
  if (!python) {
    throw new Error("Bundled AI Gateway runtime not found");
  }

  return spawnService(
    "ai_gateway",
    python,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(GATEWAY_PORT)],
    GATEWAY_DIR,
    {
      AI_GATEWAY_API_BASE_URL: `http://127.0.0.1:${API_PORT}`,
      CURRICULUM_PATH: path.join(RESOURCES, "data", "42_lausanne_curriculum.json"),
      PROGRESSION_PATH: path.join(RESOURCES, "data", "progression.json"),
    },
  );
}

function startFrontend() {
  const frontendDir = resolveFrontendDir();
  if (!frontendDir) {
    throw new Error("Frontend standalone bundle not found. Rebuild the desktop application.");
  }

  const serverPath = path.join(frontendDir, "server.js");

  return spawnService(
    "web",
    process.execPath,
    [serverPath],
    frontendDir,
    {
      ELECTRON_RUN_AS_NODE: "1",
      HOSTNAME: "127.0.0.1",
      PORT: String(WEB_PORT),
      NODE_ENV: "production",
      NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || `http://127.0.0.1:${API_PORT}`,
      NEXT_PUBLIC_AI_GATEWAY_URL:
        process.env.NEXT_PUBLIC_AI_GATEWAY_URL || `http://127.0.0.1:${GATEWAY_PORT}`,
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
    appendLog("[boot] desktop startup");

    if (hasBundledBackends()) {
      appendLog("[boot] bundled backends detected");
      startBundledApi();
      startBundledGateway();

      await healthCheck(API_PORT, "/health");
      appendLog("[boot] API is ready");

      await healthCheck(GATEWAY_PORT, "/health");
      appendLog("[boot] AI Gateway is ready");
    } else {
      appendLog("[boot] no bundled backends detected; expecting external services");
    }

    startFrontend();
    await healthCheck(WEB_PORT, "/", 60, 500, [200, 301, 302, 307, 308]);
    appendLog("[boot] frontend is ready");

    createWindow();
  } catch (error) {
    appendLog(`[boot] startup failed: ${error.message}`);
    dialog.showErrorBox(
      "42-Training — Startup Error",
      `A service failed to start:\n\n${error.message}\n\nCheck the application logs for details:\n${logPath()}`,
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
