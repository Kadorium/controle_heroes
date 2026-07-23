import type { ReactNode } from "react";
import type { HeroesSkuTriageGroup, HeroesXlsxPreviewResponse } from "../../api";
import { Badge, Button, HeroesSectionCard, type SectionStatus } from "../../components";
import { emptyDash, productCategoryLabel } from "../../i18n/glossario";
import {
  HeroesFinancialReviewSection,
  type FinancialReview,
} from "./HeroesFinancialReviewSection";
import {
  HeroesSkuTriagePanel,
  isInvoiceItemSkuPending,
} from "./HeroesSkuTriagePanel";

const CATEGORY_OPTIONS = ["RACKET", "BALL", "BAG_ACCESSORY", "APPAREL", "PICKLEBALL", "OTHER"] as const;
const INVOICE_ITEMS_PAGE_SIZE = 50;

export type CommitButtonMode = "disabled" | "green" | "yellow";

export interface Step4CommitState {
  mode: CommitButtonMode;
  label: string;
  title?: string;
}

interface Props {
  preview: HeroesXlsxPreviewResponse;
  confirmedOrder: string;
  onConfirmedOrderChange: (value: string) => void;
  provisionRate: string;
  onProvisionRateChange: (value: string) => void;
  financialReview: FinancialReview;
  versatoOverride: string;
  onVersatoOverrideChange: (value: string) => void;
  accontoOverrides: Record<string, string>;
  onAccontoOverrideChange: (invoice: string, value: string) => void;
  confirmFinancialReview: boolean;
  onConfirmFinancialReviewChange: (checked: boolean) => void;
  skuTriageGroups: HeroesSkuTriageGroup[];
  skuOpenCount: number;
  skuResolvedCount: number;
  skuTotalCount: number;
  skuDraftAliases: string[];
  onSkuResolved: () => void | Promise<void>;
  confirmDaSpedireSkip: boolean;
  onConfirmDaSpedireSkipChange: (checked: boolean) => void;
  categoryOverrides: Record<string, string>;
  onCategoryOverrideChange: (name: string, category: string) => void;
  invoicePage: number;
  onInvoicePageChange: (page: number) => void;
  commitState: Step4CommitState;
  onCommit: () => void;
  onExportXlsx: () => void;
  onExportZip: () => void;
  loading: boolean;
  error: string;
  footerRef: React.RefObject<HTMLDivElement | null>;
  hasDivergence: boolean;
}

function isInvoiceItemDraft(rawName: string, draftAliases: string[]): boolean {
  const raw = rawName.trim().toLowerCase();
  return draftAliases.some((a) => a === raw);
}

function invoiceSkuBadge(
  rawName: string,
  pendingGroups: HeroesSkuTriageGroup[],
  draftAliases: string[],
): ReactNode {
  if (!rawName) return emptyDash(null);
  if (isInvoiceItemSkuPending(rawName, pendingGroups)) {
    return <Badge tone="warning">SKU pendente</Badge>;
  }
  if (isInvoiceItemDraft(rawName, draftAliases)) {
    return <Badge tone="warning">Rascunho</Badge>;
  }
  return <Badge tone="success">✓ Resolvido</Badge>;
}

export function HeroesUploadStep4Layout({
  preview,
  confirmedOrder,
  onConfirmedOrderChange,
  provisionRate,
  onProvisionRateChange,
  financialReview,
  versatoOverride,
  onVersatoOverrideChange,
  accontoOverrides,
  onAccontoOverrideChange,
  confirmFinancialReview,
  onConfirmFinancialReviewChange,
  skuTriageGroups,
  skuOpenCount,
  skuResolvedCount,
  skuTotalCount,
  skuDraftAliases,
  onSkuResolved,
  confirmDaSpedireSkip,
  onConfirmDaSpedireSkipChange,
  categoryOverrides,
  onCategoryOverrideChange,
  invoicePage,
  onInvoicePageChange,
  commitState,
  onCommit,
  onExportXlsx,
  onExportZip,
  loading,
  error,
  footerRef,
  hasDivergence,
}: Props) {
  const invoiceItems = (preview.preview?.invoice_items as Array<Record<string, unknown>>) ?? [];
  const daSpedire = (preview.preview?.da_spedire as Array<Record<string, unknown>>) ?? [];
  const newProducts = (preview.preview?.new_products as Array<Record<string, unknown>>) ?? [];
  const daSpedireMissing = daSpedire.length === 0;

  const invoicePageCount = Math.max(1, Math.ceil(invoiceItems.length / INVOICE_ITEMS_PAGE_SIZE));
  const safeInvoicePage = Math.min(invoicePage, invoicePageCount - 1);
  const pagedInvoiceItems = invoiceItems.slice(
    safeInvoicePage * INVOICE_ITEMS_PAGE_SIZE,
    (safeInvoicePage + 1) * INVOICE_ITEMS_PAGE_SIZE,
  );
  const invoiceRangeStart = invoiceItems.length ? safeInvoicePage * INVOICE_ITEMS_PAGE_SIZE + 1 : 0;
  const invoiceRangeEnd = Math.min((safeInvoicePage + 1) * INVOICE_ITEMS_PAGE_SIZE, invoiceItems.length);

  const needsFinancialConfirm = financialReview.requires_manual_review === true;
  const financialOk = !needsFinancialConfirm || confirmFinancialReview;
  const financialStatus: SectionStatus = !needsFinancialConfirm
    ? "ok"
    : confirmFinancialReview
      ? "ok"
      : "warning";

  const skuTotal = skuTotalCount || skuTriageGroups.length || skuResolvedCount + skuOpenCount;
  const skuStatus: SectionStatus =
    skuOpenCount > 0 ? "pending" : skuDraftAliases.length > 0 ? "warning" : "ok";

  const daStatus: SectionStatus = daSpedireMissing ? "warning" : "ok";

  return (
    <section className="heroes-upload__section heroes-upload__preview">
      <h3>4. Revisar e importar</h3>

      {hasDivergence && (
        <p className="error">
          Divergência: nome da sheet ({preview.order_number_from_sheet_name}) ≠ conteúdo (
          {preview.order_number_from_content}). Confirme o número correto antes do commit.
        </p>
      )}
      {(preview.warnings ?? []).map((w, i) => (
        <p key={i} className="meta">
          ⚠ {w}
        </p>
      ))}
      {(preview.errors ?? []).map((w, i) => (
        <p key={i} className="error">
          {w}
        </p>
      ))}

      <label className="heroes-upload__order-field">
        Confirmar número da ordem
        <input
          value={confirmedOrder}
          onChange={(e) => onConfirmedOrderChange(e.target.value)}
          placeholder={
            preview.order_number_from_sheet_name ?? preview.order_number ?? "ex.: 758"
          }
        />
      </label>

      <p className="order-queue__meta">
        {invoiceItems.length} itens fatura · {daSpedire.length} linhas DA SPEDIRE ·{" "}
        {newProducts.length} produtos
      </p>

      <div className="heroes-upload-step4">
        <HeroesSectionCard
          title="Revisão financeira"
          status={financialStatus}
          statusLabel={
            financialStatus === "ok"
              ? "Confirmado"
              : needsFinancialConfirm
                ? "Revisão manual"
                : "Pendente"
          }
        >
          <HeroesFinancialReviewSection
            financialReview={financialReview}
            versatoOverride={versatoOverride}
            onVersatoOverrideChange={onVersatoOverrideChange}
            accontoOverrides={accontoOverrides}
            onAccontoOverrideChange={onAccontoOverrideChange}
            confirmFinancialReview={confirmFinancialReview}
            onConfirmFinancialReviewChange={onConfirmFinancialReviewChange}
            disabled={loading}
            showProvisionField
            provisionRate={provisionRate}
            onProvisionRateChange={onProvisionRateChange}
          />
        </HeroesSectionCard>

        <HeroesSectionCard
          title="SKUs"
          status={skuStatus}
          statusLabel={
            skuOpenCount > 0
              ? `${skuResolvedCount} de ${skuTotal} resolvidos`
              : skuDraftAliases.length > 0
                ? `${skuDraftAliases.length} rascunho(s)`
                : `${skuResolvedCount} de ${skuTotal || skuResolvedCount} resolvidos`
          }
          defaultOpen={skuOpenCount > 0 || skuTriageGroups.length > 0}
        >
          {skuTriageGroups.length > 0 ? (
            <HeroesSkuTriagePanel
              groups={skuTriageGroups}
              openCount={skuOpenCount}
              totalResolved={skuResolvedCount}
              onResolved={onSkuResolved}
              disabled={loading}
            />
          ) : (
            <p className="meta">Nenhum produto único na planilha para vincular.</p>
          )}
          {skuOpenCount > 0 && (
            <p className="meta heroes-upload__sku-blocker">
              Confirme os {skuOpenCount} produto(s) restante(s) antes da importação.
            </p>
          )}
        </HeroesSectionCard>

        <HeroesSectionCard
          title="Logística / DA SPEDIRE"
          status={daStatus}
          statusLabel={daSpedireMissing ? "Bloco ausente" : `${daSpedire.length} linha(s)`}
          defaultOpen={daSpedireMissing}
        >
          {daSpedireMissing ? (
            <>
              <p className="error heroes-upload__da-banner">
                Cabeçalho DA SPEDIRE não encontrado na planilha — a conferência logística ficará
                incompleta. Isso não impede a importação.
              </p>
              <label className="heroes-upload__confirm-item">
                <input
                  type="checkbox"
                  checked={confirmDaSpedireSkip}
                  onChange={(e) => onConfirmDaSpedireSkipChange(e.target.checked)}
                  disabled={loading}
                />
                <span>Entendo que a conferência logística ficará incompleta</span>
              </label>
            </>
          ) : (
            <div className="order-queue__scroll">
              <table className="sheet-table">
                <thead>
                  <tr>
                    <th>Linha</th>
                    <th>Produto</th>
                    <th className="num">Qtd</th>
                    <th className="num">Desconto</th>
                  </tr>
                </thead>
                <tbody>
                  {daSpedire.map((row, i) => (
                    <tr key={`da-${String(row.row_number ?? i)}`}>
                      <td>{String(row.row_number ?? emptyDash(null))}</td>
                      <td>{String(row.product_name_raw ?? emptyDash(null))}</td>
                      <td className="num">{String(row.quantity ?? emptyDash(null))}</td>
                      <td className="num">{String(row.discount ?? emptyDash(null))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </HeroesSectionCard>
      </div>

      {newProducts.length > 0 && (
        <div className="heroes-upload__products">
          <h4>Categorias sugeridas (Produto / Modelo)</h4>
          <table className="sheet-table">
            <thead>
              <tr>
                <th>Produto / Modelo</th>
                <th>Sugestão</th>
                <th>Confiança</th>
                <th>Ajustar</th>
              </tr>
            </thead>
            <tbody>
              {newProducts.map((p) => {
                const name = String(p.product_name_raw);
                return (
                  <tr key={name}>
                    <td>{name}</td>
                    <td>{productCategoryLabel(String(p.suggested_category))}</td>
                    <td className="num">{Number(p.category_confidence).toFixed(2)}</td>
                    <td>
                      <select
                        value={categoryOverrides[name] ?? String(p.suggested_category)}
                        onChange={(e) => onCategoryOverrideChange(name, e.target.value)}
                      >
                        {CATEGORY_OPTIONS.map((c) => (
                          <option key={c} value={c}>
                            {productCategoryLabel(c)}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="order-queue__scroll heroes-upload__invoice-table">
        <h4>Itens fatura (somente leitura)</h4>
        <div className="heroes-upload__items-head">
          <p className="meta heroes-upload__items-count">
            {invoiceItems.length > INVOICE_ITEMS_PAGE_SIZE
              ? `Mostrando ${invoiceRangeStart}–${invoiceRangeEnd} de ${invoiceItems.length} itens fatura`
              : `${invoiceItems.length} itens fatura`}
          </p>
          {invoiceItems.length > INVOICE_ITEMS_PAGE_SIZE && (
            <div className="heroes-upload__pagination">
              <Button
                variant="ghost"
                className="ui-btn--sm"
                disabled={safeInvoicePage <= 0}
                onClick={() => onInvoicePageChange(Math.max(0, safeInvoicePage - 1))}
              >
                Anterior
              </Button>
              <span className="meta">
                Página {safeInvoicePage + 1} de {invoicePageCount}
              </span>
              <Button
                variant="ghost"
                className="ui-btn--sm"
                disabled={safeInvoicePage >= invoicePageCount - 1}
                onClick={() =>
                  onInvoicePageChange(Math.min(invoicePageCount - 1, safeInvoicePage + 1))
                }
              >
                Próxima
              </Button>
            </div>
          )}
        </div>
        <table className="sheet-table">
          <thead>
            <tr>
              <th>Fatura</th>
              <th>Data</th>
              <th>Produto / Modelo</th>
              <th className="num">Qtd</th>
              <th className="num">Acconto</th>
              <th>SKU</th>
            </tr>
          </thead>
          <tbody>
            {pagedInvoiceItems.map((row, i) => {
              const rawName = String(row.product_name_raw ?? "");
              return (
                <tr key={`${safeInvoicePage}-${i}-${String(row.row_number ?? i)}`}>
                  <td>{String(row.invoice_number ?? emptyDash(null))}</td>
                  <td>{String(row.invoice_date ?? emptyDash(null))}</td>
                  <td>{rawName}</td>
                  <td className="num">{String(row.item_quantity ?? emptyDash(null))}</td>
                  <td className="num">{String(row.acconto_amount ?? emptyDash(null))}</td>
                  <td>{invoiceSkuBadge(rawName, skuTriageGroups, skuDraftAliases)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="heroes-upload__footer" ref={footerRef}>
        {error && (
          <p className="error heroes-upload__footer-error" role="alert">
            {error}
          </p>
        )}
        {!financialOk && commitState.mode === "disabled" && (
          <p className="meta">Confirme a revisão financeira para habilitar a importação.</p>
        )}
        <div className="heroes-upload__actions">
          <Button variant="secondary" onClick={onExportXlsx} disabled={loading}>
            Baixar preview XLSX (v1)
          </Button>
          <Button variant="secondary" onClick={onExportZip} disabled={loading}>
            Exportar CSVs (ZIP)
          </Button>
        </div>
        <Button
          className={
            commitState.mode === "yellow"
              ? "heroes-upload__commit heroes-upload__commit--pending"
              : commitState.mode === "green"
                ? "heroes-upload__commit heroes-upload__commit--ready"
                : "heroes-upload__commit"
          }
          onClick={onCommit}
          disabled={loading || commitState.mode === "disabled"}
          title={commitState.title}
        >
          {loading ? "Processando…" : commitState.label}
        </Button>
      </div>
    </section>
  );
}
