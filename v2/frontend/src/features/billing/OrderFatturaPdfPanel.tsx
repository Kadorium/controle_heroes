import { useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import { Button, FileUpload, Notice } from "../../ui";
import {
  canImportFattura,
  extractFatturaPdf,
  fatturaInvoiceNumber,
  importFatturaSession,
  type FatturaIntakeSession,
} from "./fatturaPdfIntake";

type Props = {
  user: User;
  orderId: number;
  onImported: (invoiceId: number) => void;
};

export function OrderFatturaPdfPanel({ user, orderId, onImported }: Props) {
  const [fileName, setFileName] = useState<string | null>(null);
  const [session, setSession] = useState<FatturaIntakeSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"extract" | "import" | null>(null);

  const canImport = canImportFattura(user);
  const invoiceNumber = session ? fatturaInvoiceNumber(session.doc) : "";
  const matches = session?.preview.line_matches ?? [];
  const matched = matches.filter((m) => m.status === "matched").length;

  async function onFile(file: File | null) {
    setError(null);
    setSession(null);
    setFileName(file?.name ?? null);
    if (!file) return;
    setBusy("extract");
    try {
      const next = await extractFatturaPdf(file, orderId);
      setSession(next);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível ler o PDF.");
    } finally {
      setBusy(null);
    }
  }

  async function onImport() {
    if (!session || !canImport) return;
    setBusy("import");
    setError(null);
    try {
      const invoiceId = await importFatturaSession(session, orderId);
      onImported(invoiceId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Não foi possível importar a fatura.");
    } finally {
      setBusy(null);
    }
  }

  if (!canImport) return null;

  return (
    <div className="stack" data-testid="order-fattura-pdf-panel" style={{ marginTop: "0.75rem" }}>
      <p className="muted">
        Fattura do fornecedor: cria a fatura em rascunho com linhas, vencimentos e o PDF vinculado.
        O código de barras do documento não vira o código interno.
      </p>
      <FileUpload
        data-testid="order-fattura-upload"
        accept="application/pdf,.pdf"
        label="Escolher PDF da fatura"
        fileName={fileName}
        disabled={busy != null}
        onFileChange={(file) => void onFile(file)}
      />
      {busy === "extract" ? <p className="muted">Lendo o PDF…</p> : null}
      {error ? (
        <Notice tone="danger" data-testid="order-fattura-error">
          {error}
        </Notice>
      ) : null}
      {session ? (
        <div data-testid="order-fattura-ready">
          <p>
            Fatura nº <strong data-testid="order-fattura-number">{invoiceNumber || "—"}</strong>
            {matches.length ? (
              <>
                {" "}
                · {matched} de {matches.length} linhas casadas com este pedido
              </>
            ) : null}
          </p>
          {matches.length > 0 ? (
            <ul className="muted" data-testid="order-fattura-lines">
              {matches.slice(0, 8).map((m) => (
                <li key={m.row_index}>
                  Código de barras {m.sku} · qtd {m.pdf_qty}
                  {m.status === "matched" ? " · casada" : ` · ${m.status}`}
                </li>
              ))}
            </ul>
          ) : null}
          <div className="actions">
            <Button
              type="button"
              data-testid="order-fattura-import"
              busy={busy === "import"}
              disabled={busy != null || !session.preview.can_commit}
              onClick={() => void onImport()}
            >
              Criar fatura a partir do PDF
            </Button>
            <Link
              className="ui-button ui-button--secondary"
              to={`/ingestion/${session.documentId}`}
            >
              Corrigir na ingestão
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}
