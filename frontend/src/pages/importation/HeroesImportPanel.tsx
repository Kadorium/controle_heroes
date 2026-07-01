import { useCallback, useEffect, useMemo, useState } from "react";
import { financeApi, importationsApi, type HeroesImportRunResponse } from "../../api";
import { Badge, Button, LoadingState } from "../../components";
import { useFxRate } from "../../context/FxRateContext";
import {
  HeroesFinancialReviewSection,
  initAccontoOverrides,
  type FinancialReview,
} from "./HeroesFinancialReviewSection";

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
      setAccontoOverrides(initAccontoOverrides(review));
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

      {!committed && (
        <HeroesFinancialReviewSection
          financialReview={financialReview}
          versatoOverride={versatoOverride}
          onVersatoOverrideChange={setVersatoOverride}
          accontoOverrides={accontoOverrides}
          onAccontoOverrideChange={(inv, value) =>
            setAccontoOverrides((prev) => ({ ...prev, [inv]: value }))
          }
          confirmFinancialReview={confirmFinancialReview}
          onConfirmFinancialReviewChange={setConfirmFinancialReview}
          disabled={committing}
          showProvisionField={!hasProvision}
          provisionRate={provisionRate}
          onProvisionRateChange={setProvisionRate}
        />
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
