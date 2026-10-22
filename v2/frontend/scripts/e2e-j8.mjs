/**
 * J#8 — aceite UI: suítes isoladas em sequência.
 * Cada suíte faz prepare fresco em epic_v2_test (:8082).
 * cat-pim por último. rux e ordine-order-ui com catálogo vazio, prepares separados.
 * cat-pim isolado; j8-close por último (walk UI reusa o banco).
 *
 * Uso (cwd=v2/frontend): npm run e2e:j8
 */
import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const npmCmd = process.platform === "win32" ? "npm.cmd" : "npm";

/** npm script suffix after e2e: */
const SUITES = [
  "j8-order-billing",
  "inc-fx-ap",
  "prof",
  "elo-10",
  "rbac",
  "logistics-ui",
  "j3-uiv",
  "ordine-order-ui",
  "rux-3b-2b",
  "j5",
  "a2",
  "cat-pim",
  "j8-close",
];

function runSuite(script, skipBuild) {
  return new Promise((resolve, reject) => {
    const env = { ...process.env };
    if (skipBuild) env.E2E_SKIP_BUILD = "1";
    console.log(`\n======== e2e:${script} skipBuild=${skipBuild ? "1" : "0"} ========`);
    const child = spawn(npmCmd, ["run", `e2e:${script}`], {
      cwd: frontendRoot,
      env,
      stdio: "inherit",
      shell: true,
    });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`e2e:${script} exited ${code}`));
    });
  });
}

async function main() {
  const started = new Date().toISOString();
  const results = [];
  for (let i = 0; i < SUITES.length; i++) {
    const name = SUITES[i];
    const t0 = Date.now();
    try {
      await runSuite(name, i > 0);
      results.push({ suite: name, status: "PASS", ms: Date.now() - t0 });
    } catch (err) {
      results.push({
        suite: name,
        status: "FAIL",
        ms: Date.now() - t0,
        error: err instanceof Error ? err.message : String(err),
      });
      const outDir = path.join(frontendRoot, "..", "..", "docs", "v2", "etapa-j8");
      await mkdir(outDir, { recursive: true });
      await writeFile(
        path.join(outDir, "J8_CLOSE_E2E_RUN.json"),
        JSON.stringify({ started, finished: new Date().toISOString(), results }, null, 2),
        "utf8",
      );
      throw err;
    }
  }
  const payload = { started, finished: new Date().toISOString(), results };
  const outDir = path.join(frontendRoot, "..", "..", "docs", "v2", "etapa-j8");
  await mkdir(outDir, { recursive: true });
  await writeFile(path.join(outDir, "J8_CLOSE_E2E_RUN.json"), JSON.stringify(payload, null, 2), "utf8");
  console.log("\n[e2e:j8] ALL PASS");
  console.log(JSON.stringify(payload, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
