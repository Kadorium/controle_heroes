#!/usr/bin/env node
/**
 * Gera OpenAPI JSON a partir do app FastAPI e client TS (openapi-typescript + openapi-fetch).
 * Pré-requisito: v2/.venv instalado; executar a partir de v2/frontend.
 */
import { spawnSync } from "node:child_process";
import { mkdirSync, writeFileSync, existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, "..");
const v2Root = path.resolve(frontendRoot, "..");
const outDir = path.join(frontendRoot, "src", "api", "generated");
const openapiJson = path.join(outDir, "openapi.json");
const typesFile = path.join(outDir, "schema.ts");
const clientFile = path.join(outDir, "client.ts");

mkdirSync(outDir, { recursive: true });

const pyCandidates = [
  path.join(v2Root, ".venv", "Scripts", "python.exe"),
  path.join(v2Root, ".venv", "bin", "python"),
  "python",
];
const python = pyCandidates.find((p) => p === "python" || existsSync(p));
if (!python) {
  console.error("Python v2/.venv not found");
  process.exit(1);
}

const dump = `
import json
from app.foundation.create_app import create_app
app = create_app()
print(json.dumps(app.openapi(), ensure_ascii=False, indent=2))
`;

const result = spawnSync(python, ["-c", dump], {
  cwd: v2Root,
  encoding: "utf-8",
  env: { ...process.env, PYTHONPATH: v2Root },
});
if (result.status !== 0) {
  console.error(result.stderr || result.stdout);
  process.exit(result.status || 1);
}

writeFileSync(openapiJson, result.stdout, "utf-8");

const ot = spawnSync(
  process.platform === "win32" ? "npx.cmd" : "npx",
  ["openapi-typescript", openapiJson, "-o", typesFile],
  { cwd: frontendRoot, encoding: "utf-8", shell: true },
);
if (ot.status !== 0) {
  console.error(ot.stderr || ot.stdout);
  process.exit(ot.status || 1);
}

writeFileSync(
  clientFile,
  `/* eslint-disable */
/** Generated client — do not edit by hand. Run: npm run generate:api */
import createClient from "openapi-fetch";
import type { paths } from "./schema";

export const api = createClient<paths>({
  baseUrl: "",
  credentials: "include",
});

export type { paths };
`,
  "utf-8",
);

console.log("Generated:", openapiJson, typesFile, clientFile);
