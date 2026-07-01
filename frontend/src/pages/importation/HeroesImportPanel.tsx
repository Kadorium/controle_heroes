import { useCallback, useEffect, useMemo, useState } from "react";
import { financeApi, importationsApi, type HeroesImportRunResponse } from "../../api";
import { Badge, Button, LoadingState } from "../../components";
import { useFxRate } from "../../context/FxRateContext";

interface InvoiceBlock {
  invoice_number?: string | null;
  invoice_date?: string | null;
  acconto_remaining?: string | null;
  acconto_payments?: Array<{ amount: string; receipt_reference?: string }>;
  items?: Array<{
    row_number?: number;
    product_name_raw?: string;
    item_quantity?: number | null;
  }>;
}

interface FinancialReview {
  versato_amount?: string | null;
  versato_currency?: string | null;
  acconto_total?: string | null;
  last_acconto_rimasto?: string | null;
  expected_rimasto?: string | null;
  delta_rimasto?: string | null;
  delta_versato?: string | null;
  warnings?: string[];
  requires_manual_review?: boolean;
  invoice_rows?: Array<{
    invoice_number: string;
    invoice_date?: string | null;
    acconto_amount?: string | null;
    acconto_remaining?: string | null;
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
  const [versatoOverride, setVersatoOverride] = useState("");
  const [accontoOverrides, setAccontoOverrides] = useState<Record<string, string>>({});
  const [confirmFinancialReview, setConfirmFinancialReview] = useState(false);
  const [provisionRate, setProvisionRate] = useState("");
  const [hasProvision, setHasProvision] = useState(false);
  const { reference: fxRef } = useFxRate();

  useEffect(() => {
    if (fxRef?.rate && !provisionRate) setProvisionRate(fxRef.rate);
  }, [fxRef?.rate, provisionRate]);

  useEffect(() => {
    financeApi.fxPnlForImportation(importationId).then((p) => {
      setHasProvision(!!p.provision_rate);
    }).catch(() => setHasProvision(false));
  }, [importationId]);

  const loadPreview = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const data = await importationsApi.heroesImportPreview(importationId);
      setRun(data);
      const review = (data.preview.financial_review ?? {}) as FinancialReview;
      setVersatoOverride(review.versato_amount ?? "");
      const rows = review.invoice_rows ?? [];
      const initial: Record<string, string> = {};
      for (const row of rows) {
        if (row.invoice_number && row.acconto_amount) {
          initial[row.invoice_number] = row.acconto_amount;
        }
      }
      setAccontoOverrides(initial);
      setConfirmFinancialReview(false);
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

  const financialReview = useMemo(
    () => (run?.preview.financial_review ?? {}) as FinancialReview,
    [run],
  );

  async function handleCommit() {
    setCommitting(true);
    setError("");
    try {
      const result = await importationsApi.heroesImportCommit(importationId, {
        confirmImport: true,
        confirmSheetMatch: true,
        confirmFinancialReview:
          financialReview.requires_manual_review ? confirmFinancialReview : true,
        versatoOverride: versatoOverride.trim() || null,
        accontoOverrides: Object.keys(accontoOverrides).length > 0 ? accontoOverrides : null,
        openingExchangeRate: hasProvision ? null : provisionRate.trim() || null,
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
  const needsFinancialConfirm = financialReview.requires_manual_review === true;

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
          {run.sku_review_open_count} grupo(s) de SKU aguardam vínculo
          {run.sku_review_line_count > 0
            ? ` (${run.sku_review_line_count} linha(s) na planilha)`
            : ""}{" "}
          na{" "}
          <a href={`/revisao?heroes_run_id=${run.run_id}`}>fila de revisão</a> antes do commit.
        </p>
      )}

      {!committed && financialReview.versato_amount != null && (
        <div className="heroes-import-panel__finance">
          <h3 className="hub-card__subtitle">Revisão financeira</h3>
          <p className="meta">
            Versato = referência da planilha. Acconto = pagamento por fatura. Acconto rimasto =
            saldo informativo do pool (não é saldo a liquidar).
          </p>

          <label className="heroes-import-panel__field">
            <span>Versato ({financialReview.versato_currency ?? "EUR"})</span>
            <input
              type="text"
              value={versatoOverride}
              onChange={(e) => setVersatoOverride(e.target.value)}
              disabled={committing}
            />
          </label>

          {!hasProvision && (
            <label className="heroes-import-panel__field">
              <span>Câmbio provisionado (EUR→BRL)</span>
              <input
                type="text"
                value={provisionRate}
                onChange={(e) => setProvisionRate(e.target.value)}
                disabled={committing}
                placeholder="Obrigatório se ordem sem provisão"
              />
            </label>
          )}

          <table className="heroes-import-panel__finance-table">
            <thead>
              <tr>
                <th>Fatura</th>
                <th>Data</th>
                <th>Acconto</th>
                <th>Rimasto (planilha)</th>
              </tr>
            </thead>
            <tbody>
              {(financialReview.invoice_rows ?? []).map((row) => (
                <tr key={row.invoice_number}>
                  <td>{row.invoice_number}</td>
                  <td>{row.invoice_date ?? "—"}</td>
                  <td>
                    <input
                      type="text"
                      className="heroes-import-panel__acconto-input"
                      value={accontoOverrides[row.invoice_number] ?? ""}
                      onChange={(e) =>
                        setAccontoOverrides((prev) => ({
                          ...prev,
                          [row.invoice_number]: e.target.value,
                        }))
                      }
                      disabled={committing}
                    />
                  </td>
                  <td>{row.acconto_remaining ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="heroes-import-panel__finance-totals meta">
            <span>Σ acconti: {financialReview.acconto_total ?? "—"}</span>
            <span>Rimasto esperado: {financialReview.expected_rimasto ?? "—"}</span>
            <span>Último rimasto: {financialReview.last_acconto_rimasto ?? "—"}</span>
          </div>

          {(financialReview.warnings?.length ?? 0) > 0 && (
            <ul className="error heroes-import-panel__finance-warnings">
              {financialReview.warnings!.map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          )}

          {needsFinancialConfirm && (
            <label className="heroes-import-panel__confirm">
              <input
                type="checkbox"
                checked={confirmFinancialReview}
                onChange={(e) => setConfirmFinancialReview(e.target.checked)}
                disabled={committing}
              />
              Revisei os valores financeiros e confirmo a importação apesar dos avisos.
            </label>
          )}
        </div>
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
          <Button
            onClick={handleCommit}
            disabled={committing || pending || (needsFinancialConfirm && !confirmFinancialReview)}
          >
            {committing ? "Importando…" : "Importar para ordem"}
          </Button>
        </div>
      )}
    </section>
  );
}
