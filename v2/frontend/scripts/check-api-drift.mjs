#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const generated = path.join(frontendRoot, "src", "api", "generated");
const files = ["openapi.json", "schema.ts", "client.ts"];

for (const f of files) {
  if (!existsSync(path.join(generated, f))) {
    console.error(`Missing generated file: ${f}. Run npm run generate:api`);
    process.exit(1);
  }
}

function hashDir(dir) {
  const h = createHash("sha256");
  for (const f of files) {
    h.update(f);
    h.update(readFileSync(path.join(dir, f)));
  }
  return h.digest("hex");
}

const before = hashDir(generated);
const backup = Object.fromEntries(files.map((f) => [f, readFileSync(path.join(generated, f))]));

const gen = spawnSync(process.platform === "win32" ? "npm.cmd" : "npm", ["run", "generate:api"], {
  cwd: frontendRoot,
  encoding: "utf-8",
  shell: true,
});
if (gen.status !== 0) {
  for (const f of files) writeFileSync(path.join(generated, f), backup[f]);
  console.error(gen.stderr || gen.stdout);
  process.exit(gen.status || 1);
}

const after = hashDir(generated);
for (const f of files) writeFileSync(path.join(generated, f), backup[f]);

if (before !== after) {
  console.error("OpenAPI client drift detected. Run: npm run generate:api");
  process.exit(1);
}
console.log("OpenAPI client is up to date.");
