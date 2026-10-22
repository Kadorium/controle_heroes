import type { User } from "../auth/types";
import {
  abandonOccurrence,
  classifyOccurrence,
  commitFatturaDocument,
  createBatch,
  deleteIngestionDocument,
  fetchFatturaPreview,
  IngestionApiError,
  runAdapter,
  uploadBatchFiles,
  type DocumentDetail,
  type FatturaPreviewOut,
} from "../ingestion/ingestionApi";

export type FatturaIntakeSession = {
  file: File;
  documentId: number;
  occurrenceId: number;
  doc: DocumentDetail;
  preview: FatturaPreviewOut;
};

function fieldVal(doc: DocumentDetail, key: string): string {
  const f = (doc.fields ?? []).find((x) => x.field_key === key);
  return String(f?.effective_value ?? f?.corrected_value ?? f?.normalized_value ?? f?.raw_value ?? "").trim();
}

export function canImportFattura(user: User): boolean {
  if (user.role === "admin") return true;
  const perms = user.permissions ?? [];
  return (
    perms.includes("ingestion:commit") &&
    perms.includes("orders:write") &&
    perms.includes("billing:write")
  );
}

export async function extractFatturaPdf(file: File, orderId: number): Promise<FatturaIntakeSession> {
  if (!file.name.toLowerCase().endsWith(".pdf") && file.type && !file.type.includes("pdf")) {
    throw new Error("Envie um PDF de Fattura (fatura do fornecedor).");
  }
  const batch = await createBatch("fattura-order-ui");
  const uploaded = await uploadBatchFiles(batch.id, [file]);
  const occurrence = uploaded.results[0];
  if (!occurrence) throw new Error("O arquivo não foi recebido.");
  const classified = await classifyOccurrence(occurrence.id).catch(() => ({ suggestions: [] }));
  const fatturaHint = classified.suggestions.find(
    (s) => s.adapter_id === "fattura_heroes_v1" || /fattura/i.test(s.doc_type),
  );
  const ordineHint = classified.suggestions.find((s) => /ordine/i.test(s.doc_type + s.adapter_id));
  if (ordineHint && !fatturaHint) {
    await abandonOccurrence(occurrence.id).catch(() => undefined);
    throw new Error("Este PDF parece um pedido de compra (Ordine), não uma fatura.");
  }
  const adapterId = fatturaHint?.adapter_id || "fattura_heroes_v1";
  const doc = await runAdapter(occurrence.id, { adapter_id: adapterId });
  if (doc.doc_type !== "FATTURA_VENDITA") {
    await abandonOccurrence(occurrence.id).catch(() => undefined);
    throw new Error("Não foi possível ler este arquivo como Fattura.");
  }
  const preview = await fetchFatturaPreview(doc.id, "A", orderId, false, null, []);
  return {
    file,
    documentId: doc.id,
    occurrenceId: occurrence.id,
    doc,
    preview,
  };
}

export function fatturaInvoiceNumber(doc: DocumentDetail): string {
  return fieldVal(doc, "invoice_number");
}

export async function importFatturaSession(
  session: FatturaIntakeSession,
  orderId: number,
): Promise<number> {
  const preview = await fetchFatturaPreview(session.documentId, "A", orderId, false, null, []);
  if (!preview.can_commit) {
    const unmatched = (preview.line_matches ?? []).filter((m) => m.status !== "matched");
    if (unmatched.length) {
      throw new Error(
        "Há linhas da fatura sem produto correspondente neste pedido. Vincule o catálogo (código interno ≠ código de barras) e tente de novo.",
      );
    }
    throw new Error("Ainda não é possível criar a fatura a partir deste PDF.");
  }
  const result = await commitFatturaDocument(session.documentId, {
    operation_key: `fattura-order-ui-${session.documentId}-${Date.now()}`,
    policy: "A",
    order_id: orderId,
    line_choices: [],
  });
  if (result.status !== "SUCCEEDED") {
    const failed = (result.operations ?? []).find((o) => o.status === "FAILED");
    throw new Error(failed?.error_message || "Não foi possível criar a fatura a partir do PDF.");
  }
  const invoiceOp = (result.operations ?? []).find((o) => o.entity_type === "invoice" && o.entity_id);
  const invoiceId = Number(invoiceOp?.entity_id ?? preview.last_succeeded_invoice_id);
  if (!Number.isFinite(invoiceId)) {
    throw new Error("Fatura criada, mas o identificador não veio na resposta.");
  }
  return invoiceId;
}

export async function discardFatturaIntake(session: FatturaIntakeSession): Promise<void> {
  try {
    await deleteIngestionDocument(session.documentId);
  } catch (err) {
    if (err instanceof IngestionApiError && err.status === 404) return;
    await abandonOccurrence(session.occurrenceId).catch(() => undefined);
  }
}
