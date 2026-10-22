import type { User } from "../auth/types";
import {
  abandonOccurrence,
  classifyOccurrence,
  commitIngestionDocument,
  correctIngestionField,
  createBatch,
  deleteIngestionDocument,
  fetchCommitPreview,
  fetchIngestionDocument,
  IngestionApiError,
  patchIngestionIssue,
  runAdapter,
  setIngestionOrderCode,
  uploadBatchFiles,
  type DocumentDetail,
  type PreviewCommitOut,
} from "../ingestion/ingestionApi";
import { isOrdineDocType } from "./mapOrdinePreviewToForm";

export type OrdineIntakeSession = {
  file: File;
  documentId: number;
  occurrenceId: number;
  doc: DocumentDetail;
  preview: PreviewCommitOut;
  supplierWillBeCreated: boolean;
};

function fieldOf(doc: DocumentDetail, key: string) {
  return (doc.fields ?? []).find((x) => x.field_key === key);
}

function fieldVal(doc: DocumentDetail, key: string): string {
  const f = fieldOf(doc, key);
  return String(f?.effective_value ?? f?.corrected_value ?? f?.normalized_value ?? f?.raw_value ?? "").trim();
}

export function canExtractOrdine(user: User): boolean {
  return user.role === "admin" || (user.permissions ?? []).includes("ingestion:write");
}

export function canImportOrdineCommit(user: User): boolean {
  if (user.role === "admin") return true;
  const perms = user.permissions ?? [];
  return perms.includes("ingestion:commit") && perms.includes("orders:write");
}

async function ensureSupplierIntent(doc: DocumentDetail): Promise<DocumentDetail> {
  const catalogId = fieldVal(doc, "supplier_id_catalog");
  if (/^\d+$/.test(catalogId)) return doc;
  const name = fieldVal(doc, "supplier_name");
  if (!name) return doc;
  const field = fieldOf(doc, "pending_create_supplier");
  if (!field) return doc;
  const already = fieldVal(doc, "pending_create_supplier");
  if (already) {
    try {
      const parsed = JSON.parse(already) as { name?: string };
      if (parsed?.name) return doc;
    } catch {
      /* continue */
    }
  }
  await correctIngestionField(field.id, {
    corrected_value: JSON.stringify({ name, code: null, country_code: "IT" }),
    expected_version: field.version,
    reason: "intent: criar fornecedor a partir do Ordine na tela de pedido",
  });
  const supplierIssue = (doc.issues ?? []).find(
    (i) => i.status === "OPEN" && /SUPPLIER/i.test(i.code),
  );
  if (supplierIssue) {
    await patchIngestionIssue(supplierIssue.id, { status: "RESOLVED" }).catch(() => undefined);
  }
  return fetchIngestionDocument(doc.id);
}

export async function extractOrdinePdf(file: File): Promise<OrdineIntakeSession> {
  if (!file.name.toLowerCase().endsWith(".pdf") && file.type && !file.type.includes("pdf")) {
    throw new Error("Envie um PDF de Ordine (pedido de compra).");
  }
  const batch = await createBatch("ordine-order-ui");
  const uploaded = await uploadBatchFiles(batch.id, [file]);
  const occurrence = uploaded.results[0];
  if (!occurrence) throw new Error("O arquivo não foi recebido.");
  const classified = await classifyOccurrence(occurrence.id).catch(() => ({ suggestions: [] }));
  const ordineHint = classified.suggestions.find(
    (s) => s.adapter_id === "ordine_heroes_v1" || isOrdineDocType(s.doc_type),
  );
  const fatturaHint = classified.suggestions.find((s) => /fattura/i.test(s.doc_type + s.adapter_id));
  if (fatturaHint && !ordineHint) {
    await abandonOccurrence(occurrence.id).catch(() => undefined);
    throw new Error("Este PDF parece uma fatura, não um pedido de compra (Ordine).");
  }
  const adapterId = ordineHint?.adapter_id || "ordine_heroes_v1";
  let doc = await runAdapter(occurrence.id, { adapter_id: adapterId });
  if (!isOrdineDocType(doc.doc_type)) {
    await abandonOccurrence(occurrence.id).catch(() => undefined);
    throw new Error("Não foi possível ler este arquivo como Ordine.");
  }
  doc = await ensureSupplierIntent(doc);
  const preview = await fetchCommitPreview(doc.id);
  return {
    file,
    documentId: doc.id,
    occurrenceId: occurrence.id,
    doc,
    preview,
    supplierWillBeCreated: (preview.operations ?? []).some((o) => o.op_key === "create_supplier"),
  };
}

export async function importOrdineSession(
  session: OrdineIntakeSession,
  orderCode?: string,
): Promise<number> {
  const wanted = (orderCode ?? "").trim();
  const createOp = (session.preview.operations ?? []).find((o) => o.op_key === "create_order");
  const current = String(createOp?.params?.code ?? "").trim();
  if (wanted && wanted !== current) {
    const fresh = await fetchIngestionDocument(session.documentId);
    await setIngestionOrderCode(session.documentId, {
      order_code: wanted,
      expected_version: fresh.version,
      reason: "código na tela de pedido",
    });
  }
  const preview = await fetchCommitPreview(session.documentId);
  if (!preview.can_commit) {
    const why = (preview.blocking_reasons ?? []).filter(Boolean).join(" ");
    throw new Error(why || "Ainda não é possível criar o pedido a partir deste PDF.");
  }
  const result = await commitIngestionDocument(session.documentId, {
    operation_key: `ordine-order-ui-${session.documentId}-${Date.now()}`,
  });
  if (result.status !== "SUCCEEDED") {
    const failed = (result.operations ?? []).find((o) => o.status === "FAILED");
    throw new Error(failed?.error_message || "Não foi possível criar o pedido a partir do PDF.");
  }
  const orderOp = (result.operations ?? []).find((o) => o.entity_type === "order" && o.entity_id);
  const orderId = Number(orderOp?.entity_id);
  if (!Number.isFinite(orderId)) throw new Error("Pedido criado, mas o identificador não veio na resposta.");
  return orderId;
}

export async function discardOrdineIntake(session: OrdineIntakeSession): Promise<void> {
  try {
    await deleteIngestionDocument(session.documentId);
  } catch (err) {
    if (err instanceof IngestionApiError && err.status === 404) return;
    await abandonOccurrence(session.occurrenceId).catch(() => undefined);
  }
}
