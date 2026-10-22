import {
  abandonOccurrence,
  classifyOccurrence,
  commitXlsxDocument,
  createBatch,
  deleteIngestionDocument,
  fetchIngestionDocument,
  fetchXlsxPreview,
  IngestionApiError,
  runAdapterXlsx,
  uploadBatchFiles,
  type DocumentDetail,
  type XlsxPreviewOut,
} from "../ingestion/ingestionApi";

export type XlsxIntakeSession = {
  file: File;
  documentId: number;
  occurrenceId: number;
  doc: DocumentDetail;
  preview: XlsxPreviewOut;
};

function isXlsx(file: File): boolean {
  const n = file.name.toLowerCase();
  return n.endsWith(".xlsx") || n.endsWith(".xls") || (file.type || "").includes("spreadsheet");
}

export function fileLooksLikeXlsx(file: File): boolean {
  return isXlsx(file);
}

export async function extractXlsxOrder(file: File): Promise<XlsxIntakeSession> {
  if (!isXlsx(file)) {
    throw new Error("Envie uma planilha de Ordine (.xlsx).");
  }
  const batch = await createBatch("ordine-xlsx-order-ui");
  const uploaded = await uploadBatchFiles(batch.id, [file]);
  const occurrence = uploaded.results[0];
  if (!occurrence) throw new Error("O arquivo não foi recebido.");
  await classifyOccurrence(occurrence.id).catch(() => ({ suggestions: [] }));
  const ran = await runAdapterXlsx(occurrence.id);
  const documentId = ran.document_id;
  const doc = await fetchIngestionDocument(documentId);
  if (doc.doc_type !== "ORDINE_COMPRA_XLSX") {
    await abandonOccurrence(occurrence.id).catch(() => undefined);
    throw new Error("Não foi possível ler esta planilha como Ordine.");
  }
  const preview = await fetchXlsxPreview(documentId);
  return { file, documentId, occurrenceId: occurrence.id, doc, preview };
}

export async function importXlsxSession(session: XlsxIntakeSession): Promise<number> {
  const preview = await fetchXlsxPreview(session.documentId);
  if (!preview.can_commit) {
    throw new Error("Ainda não é possível criar o pedido a partir desta planilha.");
  }
  const result = await commitXlsxDocument(
    session.documentId,
    `xlsx-order-ui-${session.documentId}-${Date.now()}`,
  );
  if (result.status !== "SUCCEEDED" && result.status !== "PARTIAL") {
    throw new Error("Não foi possível criar o pedido a partir da planilha.");
  }
  const orderOp = (result.operations ?? []).find((o) => o.entity_type === "order" && o.entity_id);
  const orderId = Number(orderOp?.entity_id);
  if (!Number.isFinite(orderId)) {
    throw new Error("Pedido criado, mas o identificador não veio na resposta.");
  }
  return orderId;
}

export async function discardXlsxIntake(session: XlsxIntakeSession): Promise<void> {
  try {
    await deleteIngestionDocument(session.documentId);
  } catch (err) {
    if (err instanceof IngestionApiError && err.status === 404) return;
    await abandonOccurrence(session.occurrenceId).catch(() => undefined);
  }
}
