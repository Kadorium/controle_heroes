export type DemoManifest = {
  schema_version: number;
  scenario_id: string;
  label: string;
  logical_database: string;
  ids: Record<string, number>;
  expected: Record<string, string>;
  checks: { path: string; fields: Record<string, unknown> }[];
  documents: { id: number; url: string; sha256: string }[];
};

export function pointer(value: unknown, path: string): unknown {
  return path.split(".").reduce<unknown>((v, key) => {
    if (key === "length" && Array.isArray(v)) return v.length;
    return v != null ? (v as Record<string, unknown>)[key] : undefined;
  }, value);
}

export async function readJson(path: string, signal: AbortSignal) {
  const r = await fetch(path, { signal, credentials: "include", cache: "no-store" });
  if (!r.ok) throw new Error(`Leitura indisponível: ${path} (HTTP ${r.status}).`);
  if (!r.headers.get("content-type")?.includes("application/json")) throw new Error(`Arquivo de demonstração não servido como JSON: ${path}. Confira o build e o manifesto do runtime.`);
  return r.json();
}

// Only same-origin read endpoints. A manifest is data, never executable steps.
export async function validateManifest(signal: AbortSignal): Promise<DemoManifest> {
  if (!["127.0.0.1", "localhost"].includes(window.location.hostname)) {
    throw new Error("A demonstração requer o runtime local isolado.");
  }
  const health = await readJson("/api/health", signal);
  if (health.logical_database !== "epic_v2_test" || health.app_env !== "test" || !health.schema_ok) {
    throw new Error("Isolamento não confirmado: esperado epic_v2_test com schema válido.");
  }
  const manifest = await readJson("/assets/demo-manifest.json", signal) as DemoManifest;
  if (manifest.schema_version !== 1 || manifest.logical_database !== health.logical_database ||
      !manifest.scenario_id?.startsWith("DEMO-") || !Array.isArray(manifest.checks) || manifest.checks.length < 10 ||
      !Array.isArray(manifest.documents) || !manifest.documents.length ||
      ["order", "invoice", "payment", "shipment", "process", "product", "case", "commercial_document"].some(k => !Number.isSafeInteger(manifest.ids?.[k]) || manifest.ids[k] < 1)) {
    throw new Error("Manifesto de demonstração ausente ou incompatível. Não houve preparação automática de dados.");
  }
  for (const check of manifest.checks) {
    if (!/^\/api\/(orders|invoices|payments|shipments|import-processes|inventory|costing)(\/[\w/-]+)?$/.test(check.path) && !/^\/api\/reporting\/stock-explorer\?product_id=\d+$/.test(check.path)) {
      throw new Error("Endpoint não permitido no manifesto.");
    }
    const actual = await readJson(check.path, signal);
    for (const [key, expected] of Object.entries(check.fields)) {
      if (JSON.stringify(pointer(actual, key)) !== JSON.stringify(expected)) {
        throw new Error(`Cenário alterado em ${check.path}, campo ${key}. Revalide o manifesto antes de apresentar.`);
      }
    }
  }
  for (const doc of manifest.documents) {
    if (doc.url !== `/api/documents/${doc.id}/content`) throw new Error("Documento fora do cenário.");
    const r = await fetch(doc.url, { signal, credentials: "include", cache: "no-store" });
    if (!r.ok) throw new Error(`Documento ${doc.id} indisponível.`);
    const hash = await crypto.subtle.digest("SHA-256", await r.arrayBuffer());
    const hex = Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, "0")).join("");
    if (hex !== doc.sha256) throw new Error(`Documento ${doc.id} diferente do manifesto.`);
  }
  return manifest;
}
