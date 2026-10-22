import { useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, FileUpload, Notice, SectionCard } from "../../ui";
import { humanPreviewSteps } from "../ingestion/ordinePreviewHuman";
import {
  canImportOrdineCommit,
  extractOrdinePdf,
  importOrdineSession,
  type OrdineIntakeSession,
} from "./ordinePdfIntake";
import { mapOrdinePreviewToForm, type OrdineFormDraft } from "./mapOrdinePreviewToForm";
import {
  extractXlsxOrder,
  fileLooksLikeXlsx,
  importXlsxSession,
  type XlsxIntakeSession,
} from "./xlsxOrderIntake";

type Props = {
  user: User;
  mode: "create" | "draft";
  onFill: (draft: OrdineFormDraft, session: OrdineIntakeSession) => void;
  onImported?: (orderId: number) => void;
};

export function OrderPdfPanel({ user, mode, onFill, onImported }: Props) {
  const [fileName, setFileName] = useState<string | null>(null);
  const [session, setSession] = useState<OrdineIntakeSession | null>(null);
  const [xlsxSession, setXlsxSession] = useState<XlsxIntakeSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"extract" | "import" | null>(null);

  const canImport = mode === "create" && canImportOrdineCommit(user);
  const draft = session ? mapOrdinePreviewToForm(session.doc, session.preview) : null;
  const steps = session ? humanPreviewSteps(session.preview.operations ?? []) : [];
  const xlsxSteps = (xlsxSession?.preview.operations ?? [])
    .map((o) => o.description)
    .filter(Boolean);

  async function onFile(file: File | null) {
    setError(null);
    setSession(null);
    setXlsxSession(null);
    setFileName(file?.name ?? null);
    if (!file) return;
    setBusy("extract");
    try {
      if (fileLooksLikeXlsx(file)) {
        const next = await extractXlsxOrder(file);
        setXlsxSession(next);
      } else {
        const next = await extractOrdinePdf(file);
        setSession(next);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível ler o arquivo.");
    } finally {
      setBusy(null);
    }
  }

  async function onImport() {
    if (!canImport) return;
    setBusy("import");
    setError(null);
    try {
      if (xlsxSession) {
        const orderId = await importXlsxSession(xlsxSession);
        onImported?.(orderId);
      } else if (session) {
        const orderId = await importOrdineSession(session);
        onImported?.(orderId);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível importar o arquivo.");
    } finally {
      setBusy(null);
    }
  }

  function onFillClick() {
    if (!session || !draft) return;
    if (draft.lines.length === 0) {
      setError("O PDF não trouxe linhas de item.");
      return;
    }
    onFill(draft, session);
  }

  return (
    <SectionCard title="A partir de um arquivo" data-testid="order-pdf-panel">
      <p className="muted">
        Ordine de compra: PDF ou planilha. Importar cria o pedido em rascunho e vincula o arquivo.
        No PDF você também pode preencher a tela para revisar.
      </p>
      <FileUpload
        data-testid="order-pdf-upload"
        accept="application/pdf,.pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,.xlsx"
        label="Escolher PDF ou planilha"
        fileName={fileName}
        disabled={busy != null}
        onFileChange={(file) => void onFile(file)}
      />
      {busy === "extract" ? <p className="muted">Lendo o arquivo…</p> : null}
      {error ? (
        <Notice tone="danger" data-testid="order-pdf-error">
          {error}
        </Notice>
      ) : null}
      {session && draft ? (
        <div data-testid="order-pdf-ready">
          {session.supplierWillBeCreated ? (
            <Notice tone="info" data-testid="order-pdf-supplier-notice">
              Fornecedor {draft.newSupplierName || "do documento"} será cadastrado ao importar. Nada
              foi gravado ainda.
            </Notice>
          ) : null}
          {steps.length > 0 ? (
            <ul className="muted" data-testid="order-pdf-preview-steps">
              {steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          ) : null}
          <div className="actions">
            {canImport ? (
              <Button
                type="button"
                data-testid="order-pdf-import"
                busy={busy === "import"}
                disabled={busy != null || !session.preview.can_commit}
                onClick={() => void onImport()}
              >
                Importar
              </Button>
            ) : null}
            <Button
              type="button"
              variant="secondary"
              data-testid="order-pdf-fill"
              disabled={busy != null || draft.lines.length === 0}
              onClick={onFillClick}
            >
              Preencher tela
            </Button>
            <Link className="ui-button ui-button--secondary" to={`/ingestion/${session.documentId}`}>
              Corrigir na ingestão
            </Link>
          </div>
        </div>
      ) : null}
      {xlsxSession ? (
        <div data-testid="order-xlsx-ready">
          {xlsxSteps.length > 0 ? (
            <ul className="muted" data-testid="order-xlsx-preview-steps">
              {xlsxSteps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          ) : null}
          <div className="actions">
            {canImport ? (
              <Button
                type="button"
                data-testid="order-xlsx-import"
                busy={busy === "import"}
                disabled={busy != null || !xlsxSession.preview.can_commit}
                onClick={() => void onImport()}
              >
                Importar planilha
              </Button>
            ) : null}
            <Link
              className="ui-button ui-button--secondary"
              to={`/ingestion/${xlsxSession.documentId}`}
            >
              Corrigir na ingestão
            </Link>
          </div>
        </div>
      ) : null}
    </SectionCard>
  );
}
