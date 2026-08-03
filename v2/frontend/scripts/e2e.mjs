/**
 * Bootstrap + Playwright E2E isolado (epic_v2_test @ 8082).
 *
 * npm run e2e:prepare  — só prepara o banco
 * npm run e2e          — prepare + build dist + servidor 8082 + Playwright + teardown
 *
 * Nunca usa epic_v2 / 8081.
 * O alvo HTTP é StaticFiles de frontend/dist — build é obrigatório (exceto E2E_SKIP_BUILD=1).
 */
import { spawn } from "node:child_process";
import { createWriteStream } from "node:fs";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const v2Root = path.resolve(frontendRoot, "..");
const py = path.join(v2Root, ".venv", "Scripts", "python.exe");

const E2E_PORT = process.env.E2E_PORT || "8082";
const E2E_DB_URL =
  process.env.E2E_DATABASE_URL ||
  process.env.TEST_DATABASE_URL ||
  "postgresql://postgres@localhost:5433/epic_v2_test";
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || `http://127.0.0.1:${E2E_PORT}`;

function assertTestDb(url) {
  let name = "";
  try {
    name = new URL(url).pathname.replace(/^\//, "").split("?")[0];
  } catch {
    throw new Error(`E2E_DATABASE_URL inválida: ${url}`);
  }
  if (name === "epic_v2") {
    throw new Error("REFUSADO: E2E não pode usar epic_v2 (ops).");
  }
  if (name !== "epic_v2_test") {
    throw new Error(`REFUSADO: database=${name}; exigido epic_v2_test`);
  }
}

function run(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      cwd: opts.cwd || v2Root,
      env: { ...process.env, ...opts.env },
      stdio: opts.stdio || "inherit",
      shell: opts.shell ?? false,
    });
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${cmd} ${args.join(" ")} exited ${code}`));
    });
  });
}

/**
 * Uvicorn serve `frontend/dist` (StaticFiles). Sem build, E2E mede artefato stale.
 * Skip só com E2E_SKIP_BUILD=1 (debug explícito — não usar em baseline).
 */
async function buildFrontendDist() {
  if (process.env.E2E_SKIP_BUILD === "1") {
    console.warn("[e2e] E2E_SKIP_BUILD=1 — dist NÃO reconstruído (risco de falso verde)");
    return;
  }
  console.log("[e2e] build frontend → dist (alvo servido em :8082)");
  const npmCmd = process.platform === "win32" ? "npm.cmd" : "npm";
  await run(npmCmd, ["run", "build"], { cwd: frontendRoot, shell: true });
}

async function waitHealth(url, timeoutMs = 30000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const r = await fetch(`${url}/api/health`);
      if (r.ok) return;
    } catch {
      /* retry */
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  throw new Error(`Health timeout: ${url}/api/health`);
}

async function prepare() {
  assertTestDb(E2E_DB_URL);
  console.log(`[e2e] prepare database=${new URL(E2E_DB_URL).pathname} port=${E2E_PORT}`);
  await run(py, ["scripts/e2e_prepare.py"], {
    env: { E2E_DATABASE_URL: E2E_DB_URL, DATABASE_URL: E2E_DB_URL, APP_ENV: "test" },
  });
}

async function runE2E() {
  assertTestDb(E2E_DB_URL);
  await prepare();
  await buildFrontendDist();

  const logDir = path.join(frontendRoot, "test-results");
  await mkdir(logDir, { recursive: true });
  const logPath = path.join(logDir, `e2e-server-${E2E_PORT}.log`);
  const logStream = createWriteStream(logPath, { flags: "w" });

  const startedAt = new Date().toISOString();
  console.log(`[e2e] start_server port=${E2E_PORT} db=epic_v2_test at=${startedAt}`);

  const server = spawn(
    py,
    ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", E2E_PORT],
    {
      cwd: v2Root,
      env: {
        ...process.env,
        DATABASE_URL: E2E_DB_URL,
        APP_ENV: "test",
      },
      stdio: ["ignore", "pipe", "pipe"],
      shell: false,
    },
  );

  server.stdout.pipe(logStream);
  server.stderr.pipe(logStream);
  console.log(`[e2e] server_pid=${server.pid} log=${logPath}`);

  const cleanup = () => {
    if (server.exitCode === null && !server.killed) {
      try {
        server.kill("SIGTERM");
      } catch {
        /* ignore */
      }
    }
  };
  process.on("exit", cleanup);
  process.on("SIGINT", () => {
    cleanup();
    process.exit(130);
  });

  try {
    await waitHealth(BASE_URL);
    console.log(`[e2e] health ok ${BASE_URL}`);

    const specs = process.env.E2E_SPECS
      ? process.env.E2E_SPECS.split(",")
      : ["e2e/inc5-ap-cockpit.spec.ts"];
    const playwrightCli = path.join(
      frontendRoot,
      "node_modules",
      "@playwright",
      "test",
      "cli.js",
    );
    await run(process.execPath, [playwrightCli, "test", ...specs, "--reporter=line"], {
      cwd: frontendRoot,
      env: {
        PLAYWRIGHT_BASE_URL: BASE_URL,
        E2E_DATABASE_URL: E2E_DB_URL,
      },
    });
    console.log("[e2e] playwright PASS");
  } finally {
    cleanup();
    await new Promise((r) => setTimeout(r, 500));
    logStream.end();
    console.log(`[e2e] server stopped pid=${server.pid}`);
  }
}

const mode = process.argv[2] || "run";
if (mode === "prepare") {
  prepare().catch((e) => {
    console.error(e);
    process.exit(1);
  });
} else {
  runE2E().catch((e) => {
    console.error(e);
    process.exit(1);
  });
}
