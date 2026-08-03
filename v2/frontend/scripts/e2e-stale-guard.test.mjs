/**
 * Prova estática: e2e.mjs exige build do dist antes do uvicorn.
 * Roda com: node --test scripts/e2e-stale-guard.test.mjs
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, it } from "node:test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const e2eSrc = readFileSync(path.join(__dirname, "e2e.mjs"), "utf8");

describe("e2e stale-dist guard", () => {
  it("define buildFrontendDist e chama antes de start_server", () => {
    assert.match(e2eSrc, /async function buildFrontendDist/);
    const buildCall = e2eSrc.indexOf("await buildFrontendDist()");
    const startLog = e2eSrc.indexOf("start_server");
    assert.ok(buildCall >= 0, "deve chamar await buildFrontendDist()");
    assert.ok(startLog > buildCall, "build deve ocorrer antes de start_server");
  });

  it("recusa epic_v2 e exige epic_v2_test", () => {
    assert.match(e2eSrc, /E2E não pode usar epic_v2/);
    assert.match(e2eSrc, /exigido epic_v2_test/);
  });

  it("porta default 8082 e skip de build só explícito", () => {
    assert.match(e2eSrc, /E2E_PORT \|\| "8082"/);
    assert.match(e2eSrc, /E2E_SKIP_BUILD === "1"/);
    assert.match(e2eSrc, /risco de falso verde/);
  });

  it("usa npm run build (sem watcher/daemon)", () => {
    assert.match(e2eSrc, /\["run", "build"\]/);
    assert.doesNotMatch(e2eSrc, /vite.*--watch|chokidar|nodemon/);
  });
});
