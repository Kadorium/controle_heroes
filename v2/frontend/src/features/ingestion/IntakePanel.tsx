import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, Notice, SectionCard } from "../../ui";
import {
  abandonOccurrence,
  classifyOccurrence,
  createBatch,
  fetchAdapters,
  getBatch,
  runAdapter,
  runAdapterFattura,
  runAdapterNumerario,
  uploadBatchFiles,
  type AdapterInfo,
  type ClassifySuggestion,
  type OccurrenceOut,
} from "./ingestionApi";

const BATCH_STORAGE_KEY = "epic-ingestion-active-batch-id";

type Props = {
  user: User;
  onAdapterSuccess?: () => void;
};

type FileRow = {
  clientKey: string;
  file: File;
  uploadStatus: "queued" | "uploading" | "done" | "error";
  uploadError?: string;
  occurrence?: OccurrenceOut;
  classifyStatus: "idle" | "loading" | "done" | "error";
  suggestions: ClassifySuggestion[];
  selectedAdapterId: string;
  adapterBusy: boolean;
  adapterError?: string;
  documentId?: number;
};

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("ingestion:write");
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function statusLabel(uploadStatus: string, occStatus?: string): string {
  const up: Record<string, string> = {
    queued: "Na fila",
    uploading: "Enviando",
    done: "Pronto",
    error: "Erro",
  };
  const occ: Record<string, string> = {
    STORED: "Recebido",
    ABANDONED: "Abandonado",
    REJECTED: "Rejeitado",
  };
  const a = up[uploadStatus] ?? uploadStatus;
  const b = occStatus ? occ[occStatus] ?? occStatus : "";
  return b ? `${a} · ${b}` : a;
}

function fileTypeLabel(occ: OccurrenceOut | undefined, file: File): string {
  const mime = occ?.detected_mime || occ?.declared_mime || file.type || "";
  if (mime.includes("pdf")) return "PDF";
  if (mime.includes("sheet") || mime.includes("excel") || /\.xlsx?$/i.test(file.name)) return "Planilha";
  if (mime) return mime.split("/").pop()?.toUpperCase() || "Arquivo";
  return "Arquivo";
}


async function runAdapterForOccurrence(
  occurrenceId: number,
  adapterId: string,
  docType: string,
): Promise<{ document_id: number }> {
  // Prefer unified registry for all adapters (incl. dossiê). Keep aliases only when
  // the selected id/type is exactly the Heroes Fattura / Numerário / XLSX path.
  if (adapterId === "fattura_heroes_v1" || docType === "FATTURA_VENDITA") {
    const doc = await runAdapterFattura(occurrenceId);
    return { document_id: doc.id };
  }
  if (adapterId === "solicitacao_numerario_v1" || docType === "SOLICITACAO_NUMERARIO") {
    const res = await runAdapterNumerario(occurrenceId);
    return { document_id: res.document_id };
  }
  if (adapterId === "ordine_heroes_xlsx_v1" || docType === "ORDINE_COMPRA_XLSX") {
    // Prefer unified registry — xlsx alias returns a non-Document payload shape.
    const doc = await runAdapter(occurrenceId, {
      adapter_id: "ordine_heroes_xlsx_v1",
      doc_type: "ORDINE_COMPRA_XLSX",
    });
    return { document_id: doc.id };
  }
  const doc = await runAdapter(occurrenceId, { adapter_id: adapterId, doc_type: docType || undefined });
  return { document_id: doc.id };
}

export function IntakePanel({ user, onAdapterSuccess }: Props) {
  const [batchId, setBatchId] = useState<number | null>(null);
  const [batchBusy, setBatchBusy] = useState(false);
  const [rows, setRows] = useState<FileRow[]>([]);
  const [adapters, setAdapters] = useState<AdapterInfo[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ensureBatch = useCallback(async (): Promise<number> => {
    if (batchId != null) return batchId;
    const stored = sessionStorage.getItem(BATCH_STORAGE_KEY);
    if (stored) {
      const parsed = Number(stored);
      if (Number.isFinite(parsed)) {
        setBatchId(parsed);
        return parsed;
      }
    }
    setBatchBusy(true);
    try {
      const batch = await createBatch();
      sessionStorage.setItem(BATCH_STORAGE_KEY, String(batch.id));
      setBatchId(batch.id);
      return batch.id;
    } finally {
      setBatchBusy(false);
    }
  }, [batchId]);

  useEffect(() => {
    void fetchAdapters()
      .then(setAdapters)
      .catch(() => {
        /* registry endpoint may lag OpenAPI */
      });
    const stored = sessionStorage.getItem(BATCH_STORAGE_KEY);
    if (stored) {
      const id = Number(stored);
      if (Number.isFinite(id)) {
        setBatchId(id);
        void getBatch(id)
          .then((b) => {
            setRows(
              b.occurrences.map((occ) => ({
                clientKey: `occ-${occ.id}`,
                file: new File([], occ.original_filename),
                uploadStatus: "done" as const,
                occurrence: occ,
                classifyStatus: "idle" as const,
                suggestions: [],
                selectedAdapterId: "",
                adapterBusy: false,
              })),
            );
          })
          .catch(() => sessionStorage.removeItem(BATCH_STORAGE_KEY));
      }
    }
  }, []);

  async function classifyRow(clientKey: string, occurrenceId: number) {
    setRows((prev) =>
      prev.map((r) =>
        r.clientKey === clientKey ? { ...r, classifyStatus: "loading", suggestions: [] } : r,
      ),
    );
    try {
      const result = await classifyOccurrence(occurrenceId);
      setRows((prev) =>
        prev.map((r) => {
          if (r.clientKey !== clientKey) return r;
          const first = result.suggestions[0];
          return {
            ...r,
            classifyStatus: "done",
            suggestions: result.suggestions,
            selectedAdapterId: first?.adapter_id ?? r.selectedAdapterId,
          };
        }),
      );
    } catch (e) {
      setRows((prev) =>
        prev.map((r) =>
          r.clientKey === clientKey
            ? {
                ...r,
                classifyStatus: "error",
                suggestions: [],
              }
            : r,
        ),
      );
    }
  }

  async function processFiles(fileList: FileList | File[]) {
    if (!canWrite(user)) return;
    setGlobalError(null);
    const files = Array.from(fileList);
    if (!files.length) return;

    const bid = await ensureBatch();
    const newRows: FileRow[] = files.map((file, idx) => ({
      clientKey: `${Date.now()}-${idx}-${file.name}`,
      file,
      uploadStatus: "queued",
      classifyStatus: "idle",
      suggestions: [],
      selectedAdapterId: "",
      adapterBusy: false,
    }));
    setRows((prev) => [...prev, ...newRows]);

    for (const row of newRows) {
      setRows((prev) =>
        prev.map((r) => (r.clientKey === row.clientKey ? { ...r, uploadStatus: "uploading" } : r)),
      );
      try {
        const res = await uploadBatchFiles(bid, [row.file], [row.clientKey]);
        const occ = res.results[0];
        setRows((prev) =>
          prev.map((r) =>
            r.clientKey === row.clientKey ? { ...r, uploadStatus: "done", occurrence: occ } : r,
          ),
        );
        if (occ) void classifyRow(row.clientKey, occ.id);
      } catch (e) {
        setRows((prev) =>
          prev.map((r) =>
            r.clientKey === row.clientKey
              ? {
                  ...r,
                  uploadStatus: "error",
                  uploadError: e instanceof Error ? e.message : "Falha no upload",
                }
              : r,
          ),
        );
      }
    }
  }

  async function handleRunAdapter(row: FileRow) {
    if (!row.occurrence) return;
    const adapterId =
      row.selectedAdapterId ||
      row.suggestions[0]?.adapter_id ||
      adapters[0]?.adapter_id ||
      "";
    const docType =
      row.suggestions.find((s) => s.adapter_id === adapterId)?.doc_type ||
      adapters.find((a) => a.adapter_id === adapterId)?.doc_type ||
      "";
    if (!adapterId) {
      setGlobalError("Escolha o tipo de documento antes de extrair os dados.");
      return;
    }
    setRows((prev) =>
      prev.map((r) =>
        r.clientKey === row.clientKey ? { ...r, adapterBusy: true, adapterError: undefined } : r,
      ),
    );
    try {
      const result = await runAdapterForOccurrence(row.occurrence.id, adapterId, docType);
      setRows((prev) =>
        prev.map((r) =>
          r.clientKey === row.clientKey
            ? { ...r, adapterBusy: false, documentId: result.document_id }
            : r,
        ),
      );
      onAdapterSuccess?.();
    } catch (e) {
      setRows((prev) =>
        prev.map((r) =>
          r.clientKey === row.clientKey
            ? {
                ...r,
                adapterBusy: false,
                adapterError: e instanceof Error ? e.message : "Falha no adapter",
              }
            : r,
        ),
      );
    }
  }

  async function handleAbandon(row: FileRow) {
    if (!row.occurrence) return;
    try {
      await abandonOccurrence(row.occurrence.id);
      setRows((prev) => prev.filter((r) => r.clientKey !== row.clientKey));
    } catch (e) {
      setGlobalError(e instanceof Error ? e.message : "Falha ao abandonar");
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files?.length) void processFiles(e.dataTransfer.files);
  }

  if (!canWrite(user)) return null;

  return (
    <SectionCard title="Enviar documentos" data-testid="ingestion-intake-panel">
      {globalError ? <Notice tone="danger">{globalError}</Notice> : null}
      <div className="ingestion-intake-meta">
        <span data-testid="intake-batch-id">
          Envio atual: {batchId != null ? `#${batchId}` : batchBusy ? "criando…" : "—"}
        </span>
        <Button
          type="button"
          variant="ghost"
          data-testid="intake-new-batch"
          onClick={() => {
            sessionStorage.removeItem(BATCH_STORAGE_KEY);
            setBatchId(null);
            setRows([]);
          }}
        >
          Começar novo envio
        </Button>
      </div>

      <div
        className={`ingestion-dropzone${dragOver ? " is-dragover" : ""}`}
        data-testid="intake-dropzone"
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") fileInputRef.current?.click();
        }}
      >
        <p>Arraste PDFs ou planilhas aqui, ou clique para selecionar</p>
        <p className="muted">Vários arquivos — escolha o tipo e extraia os dados de cada um</p>
      </div>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="ingestion-dropzone-input"
        data-testid="intake-file-input"
        onChange={(e) => {
          if (e.target.files?.length) void processFiles(e.target.files);
          e.target.value = "";
        }}
      />

      {rows.length > 0 ? (
        <table className="dense-table ingestion-intake-table" data-testid="intake-files-table">
          <thead>
            <tr>
              <th>Arquivo</th>
              <th>Tamanho</th>
              <th>Tipo de arquivo</th>
              <th>Status</th>
              <th>Tipo de documento</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const occ = row.occurrence;
              return (
                <tr key={row.clientKey} data-testid={`intake-row-${row.clientKey}`}>
                  <td>{occ?.original_filename ?? row.file.name}</td>
                  <td>{formatBytes(occ?.size_bytes ?? row.file.size)}</td>
                  <td>{fileTypeLabel(occ, row.file)}</td>
                  <td>
                    {statusLabel(row.uploadStatus, occ?.status)}
                    {row.uploadError ? (
                      <span className="error-text"> ({row.uploadError})</span>
                    ) : null}
                  </td>
                  <td>
                    {row.classifyStatus === "loading" ? (
                      "identificando…"
                    ) : row.suggestions.length ? (
                      <select
                        value={row.selectedAdapterId}
                        data-testid={`intake-adapter-select-${occ?.id ?? row.clientKey}`}
                        onChange={(e) =>
                          setRows((prev) =>
                            prev.map((r) =>
                              r.clientKey === row.clientKey
                                ? { ...r, selectedAdapterId: e.target.value }
                                : r,
                            ),
                          )
                        }
                      >
                        <option value="">— escolher —</option>
                        {row.suggestions.map((s) => (
                          <option key={s.adapter_id} value={s.adapter_id}>
                            {s.label}
                          </option>
                        ))}
                        {adapters
                          .filter((a) => !row.suggestions.some((s) => s.adapter_id === a.adapter_id))
                          .map((a) => (
                            <option key={a.adapter_id} value={a.adapter_id}>
                              {a.label}
                            </option>
                          ))}
                      </select>
                    ) : row.classifyStatus === "error" ? (
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={() => occ && void classifyRow(row.clientKey, occ.id)}
                      >
                        Tentar de novo
                      </Button>
                    ) : occ ? (
                      <Button
                        type="button"
                        variant="ghost"
                        data-testid={`intake-classify-${occ.id}`}
                        onClick={() => void classifyRow(row.clientKey, occ.id)}
                      >
                        Escolher tipo de documento
                      </Button>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="ingestion-intake-actions">
                    {occ ? (
                      <>
                        <Button
                          type="button"
                          disabled={row.adapterBusy}
                          data-testid={`intake-run-adapter-${occ.id}`}
                          onClick={() => void handleRunAdapter(row)}
                        >
                          {row.adapterBusy ? "Extraindo…" : "Extrair dados"}
                        </Button>
                        {row.documentId ? (
                          <Link
                            className="ui-button"
                            to={`/ingestion/${row.documentId}`}
                            data-testid={`intake-open-doc-${row.documentId}`}
                          >
                            Abrir
                          </Link>
                        ) : null}
                        <Button type="button" variant="ghost" onClick={() => void handleAbandon(row)}>
                          Remover
                        </Button>
                      </>
                    ) : null}
                    {row.adapterError ? <p className="error-text">{row.adapterError}</p> : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <p className="muted" data-testid="intake-empty-hint">
          Nenhum arquivo neste envio. Envie PDFs ou planilhas para começar.
        </p>
      )}
    </SectionCard>
  );
}
