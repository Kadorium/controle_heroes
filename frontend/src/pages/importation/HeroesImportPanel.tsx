import { useCallback, useEffect, useState } from "react";
import { importationsApi, type HeroesImportRunResponse } from "../../api";
import { Badge, Button, LoadingState } from "../../components";

interface InvoiceBlock {
  invoice_number?: string | null;
  invoice_date?: string | null;
  acconto_payments?: Array<{ amount: string; receipt_reference?: string }>;
  items?: Array<{
    row_number?: number;
    product_name_raw?: string;
    item_quantity?: number | null;
  }>;
}

interface Props {
  importationId: number;
  onCommitted?: () => void;
}

export function HeroesImportPanel({ importationId, onCommitted }: Props) {
  const [run, setRun] = useState<HeroesImportRunResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState("");

  const loadPreview = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRun(await importationsApi.heroesImportPreview(importationId));
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Erro ao carregar preview Heroes";
      if (msg.includes("404") || msg.toLowerCase().includes("vínculo")) {
        setRun(null);
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  }, [importationId]);

  useEffect(() => {
    loadPreview();
  }, [loadPreview]);

  async function handleCommit() {
    setCommitting(true);
    setError("");
    try {
      const result = await importationsApi.heroesImportCommit(importationId, {
        confirmImport: true,
        confirmSheetMatch: true,
      });
      setRun(result);
      onCommitted?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Commit falhou");
    } finally {
      setCommitting(false);
    }
  }

  if (loading) {
    return <LoadingState label="Carregando planilha Heroes vinculada..." />;
  }

  if (!run) {
    return null;
  }

  const blocks = (run.preview.invoice_blocks ?? []) as InvoiceBlock[];
  const pending = run.sku_review_open_count > 0 || run.sku_review_pending;
  const committed = run.status === "COMMITTED";

  return (
    <section className="card heroes-import-panel" aria-label="Importação Heroes">
      <div className="heroes-import-panel__head">
        <h2 className="hub-card__title">Planilha Heroes — {run.sheet_name}</h2>
        <Badge tone={committed ? "success" : pending ? "warning" : "info"}>
          {committed ? "Importada" : pending ? "SKUs pendentes" : run.status}
        </Badge>
      </div>

      {error && <p className="error">{error}</p>}

      {run.merge_warnings?.length > 0 && (
        <ul className="meta heroes-import-panel__warnings">
          {run.merge_warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}

      {pending && (
        <p className="meta">
          {run.sku_review_open_count} produto(s) aguardam vínculo de SKU na{" "}
          <a href="/revisao">fila de revisão</a> antes do commit.
        </p>
      )}

      <div className="heroes-import-panel__blocks">
        {blocks.map((block) => {
          const inv = block.invoice_number ?? "—";
          const accontos = block.acconto_payments ?? [];
          const accontoLabel =
            accontos.length === 0
              ? "—"
              : accontos.map((p) => `${p.amount} EUR`).join(" + ");
          return (
            <div key={inv} className="heroes-import-panel__block">
              <header className="heroes-import-panel__block-head">
                <strong>Fatura {inv}</strong>
                <span className="meta">{block.invoice_date ?? "—"}</span>
                <span>Acconto: {accontoLabel}</span>
              </header>
              <ul className="heroes-import-panel__items">
                {(block.items ?? []).map((item) => (
                  <li key={`${inv}-${item.row_number}-${item.product_name_raw}`}>
                    {item.item_quantity ?? "—"} × {item.product_name_raw}
                    {pending && <span className="meta"> — SKU pendente</span>}
                  </li>
                ))}
                {(block.items ?? []).length === 0 && (
                  <li className="meta">Sem itens (somente acconto)</li>
                )}
              </ul>
            </div>
          );
        })}
      </div>

      {!committed && (
        <div className="heroes-import-panel__actions">
          <Button variant="ghost" onClick={loadPreview} disabled={committing}>
            Atualizar preview
          </Button>
          <Button onClick={handleCommit} disabled={committing || pending}>
            {committing ? "Importando…" : "Importar para ordem"}
          </Button>
        </div>
      )}
    </section>
  );
}
