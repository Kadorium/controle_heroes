/**
 * Carrega um manifest de specs e executa npm run e2e com E2E_SPECS.
 * Uso: node scripts/e2e-suite.mjs horizon-a
 * Preserva build obrigatório via e2e.mjs.
 */
import { readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");

const suiteName = process.argv[2];
if (!suiteName) {
  console.error("Uso: node scripts/e2e-suite.mjs <suite>");
  console.error("Suites: horizon-a | inc-6");
  process.exit(1);
}

const manifestPath = path.join(frontendRoot, "e2e", "suites", `${suiteName}.txt`);
let raw;
try {
  raw = readFileSync(manifestPath, "utf8");
} catch {
  console.error(`Manifest não encontrado: ${manifestPath}`);
  process.exit(1);
}

const specs = raw
  .split(/\r?\n/)
  .map((l) => l.trim())
  .filter((l) => l && !l.startsWith("#"));

if (specs.length === 0) {
  console.error(`Manifest vazio: ${manifestPath}`);
  process.exit(1);
}

const E2E_SPECS = specs.join(",");
console.log(`[e2e-suite] suite=${suiteName} specs=${specs.length}`);
console.log(`[e2e-suite] ${E2E_SPECS}`);

const npmCmd = process.platform === "win32" ? "npm.cmd" : "npm";
const child = spawn(npmCmd, ["run", "e2e"], {
  cwd: frontendRoot,
  env: { ...process.env, E2E_SPECS },
  stdio: "inherit",
  shell: true,
});

child.on("exit", (code) => process.exit(code ?? 1));
child.on("error", (err) => {
  console.error(err);
  process.exit(1);
});
