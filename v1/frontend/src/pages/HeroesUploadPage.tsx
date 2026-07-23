import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  importsApi,
  type HeroesWorkbookProfileResponse,
  type HeroesXlsxPreviewResponse,
  type HeroesXlsxSheetInfo,
  type HeroesXlsxUploadResponse,
} from "../api";
import { Button, Card, LoadingState, PageHeader, useToast } from "../components";
import { useFxRate } from "../context/FxRateContext";
import { emptyDash } from "../i18n/glossario";
import {
  initAccontoOverrides,
  type FinancialReview,
} from "./importation/HeroesFinancialReviewSection";
import {
  HeroesUploadStep4Layout,
  type Step4CommitState,
} from "./importation/HeroesUploadStep4Layout";

type LoadingPhase = "idle" | "preview" | "sku-sync" | "commit";

function resolveOrderNumberForSheet(
  sheets: HeroesXlsxSheetInfo[],
  sheetName: string,
): string {
  const sheet = sheets.find((s) => s.sheet_name === sheetName);
  if (!sheet) return "";
  return String(sheet.order_number_from_content || sheet.order_number_hint || "").trim();
}

function resolveOrderFromPreview(
  p: HeroesXlsxPreviewResponse,
  sheetFallback: string,
): string {
  return (
    p.order_number_from_content?.trim() ||
    p.order_number_from_sheet_name?.trim() ||
    p.order_number?.trim() ||
    sheetFallback
  );
}

function parseAttachedOrderId(message: string): number | null {
  const match = message.match(/\(#(\d+)\)/);
  return match ? Number(match[1]) : null;
}

export function HeroesUploadPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const footerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [locateMsg, setLocateMsg] = useState("");
  const [upload, setUpload] = useState<HeroesXlsxUploadResponse | null>(null);
  const [profile, setProfile] = useState<HeroesWorkbookProfileResponse | null>(null);
  const [selectedSheet, setSelectedSheet] = useState("");
  const [preview, setPreview] = useState<HeroesXlsxPreviewResponse | null>(null);
  const [categoryOverrides, setCategoryOverrides] = useState<Record<string, string>>({});
  const [confirmedOrder, setConfirmedOrder] = useState("");
  const [provisionRate, setProvisionRate] = useState("");
  const [csvMsg, setCsvMsg] = useState("");
  const { reference: fxRef } = useFxRate();

  useEffect(() => {
    if (fxRef?.rate && !provisionRate) setProvisionRate(fxRef.rate);
  }, [fxRef?.rate, provisionRate]);
  const [attachedOrderId, setAttachedOrderId] = useState<number | null>(null);
  const [invoicePage, setInvoicePage] = useState(0);
  const [versatoOverride, setVersatoOverride] = useState("");
  const [accontoOverrides, setAccontoOverrides] = useState<Record<string, string>>({});
  const [confirmFinancialReview, setConfirmFinancialReview] = useState(false);
  const [confirmDaSpedireSkip, setConfirmDaSpedireSkip] = useState(false);
  const [loadingPhase, setLoadingPhase] = useState<LoadingPhase>("idle");

  useEffect(() => {
    importsApi
      .locateHeroesWorkbook()
      .then((r) => {
        if (r.found) {
          setLocateMsg(`Planilha legada encontrada: ${r.resolved_path}`);
        } else {
          setLocateMsg(`Planilha não encontrada. Procurando em: ${r.search_paths.join(", ")}`);
        }
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!upload || !selectedSheet) return;
    const ord = resolveOrderNumberForSheet(upload.sheets, selectedSheet);
    if (ord) setConfirmedOrder(ord);
    setPreview(null);
    setError("");
    setAttachedOrderId(null);
    setInvoicePage(0);
    setConfirmDaSpedireSkip(false);
  }, [selectedSheet, upload?.raw_file_id]);

  function loadingLabel(): string {
    if (loadingPhase === "preview") return "Analisando planilha…";
    if (loadingPhase === "sku-sync") return "Verificando produtos…";
    if (loadingPhase === "commit") return "Criando ordem…";
    return "Processando planilha…";
  }

  async function handleLoadLocal() {
    setError("");
    setPreview(null);
    setLoading(true);
    try {
      const res = await importsApi.loadHeroesWorkbookLocal();
      applyUpload(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao carregar planilha local");
    } finally {
      setLoading(false);
    }
  }

  async function handleAnalyzeOnly() {
    setError("");
    setLoading(true);
    try {
      const p = await importsApi.profileHeroesWorkbook();
      setProfile(p);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Não foi possível analisar a planilha.");
    } finally {
      setLoading(false);
    }
  }

  function applyUpload(res: HeroesXlsxUploadResponse) {
    setUpload(res);
    setProfile(res.workbook_profile ?? null);
    setSelectedSheet("");
    setConfirmedOrder("");
  }

  async function handleXlsx(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    setPreview(null);
    setUpload(null);
    setLoading(true);
    try {
      const res = await importsApi.uploadHeroesXlsx(file);
      applyUpload(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro no upload");
    } finally {
      setLoading(false);
    }
  }

  async function handleCsv(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError("");
    try {
      const result = await importsApi.uploadHeroes(file);
      setCsvMsg(`CSV recebido: ${result.row_count ?? 0} linhas enviadas para revisão.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro CSV");
    }
  }

  async function loadPreview(skuResync = false) {
    if (!upload || !selectedSheet) return;
    setLoading(true);
    setLoadingPhase(skuResync ? "sku-sync" : "preview");
    setError("");
    const sheetOrder = resolveOrderNumberForSheet(upload.sheets, selectedSheet);
    try {
      const p = await importsApi.previewHeroesXlsx(
        upload.raw_file_id,
        selectedSheet,
        sheetOrder || undefined,
      );
      setPreview(p);
      setConfirmedOrder(resolveOrderFromPreview(p, sheetOrder));
      setInvoicePage(0);
      setConfirmDaSpedireSkip(false);
      const review = (p.preview?.financial_review ?? {}) as FinancialReview;
      setVersatoOverride(review.versato_amount ?? "");
      setAccontoOverrides(initAccontoOverrides(review));
      setConfirmFinancialReview(false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro no preview";
      setError(msg);
      setAttachedOrderId(parseAttachedOrderId(msg));
      toast.error(msg);
    } finally {
      setLoading(false);
      setLoadingPhase("idle");
    }
  }

  async function commitImport() {
    if (!preview) return;
    setLoading(true);
    setLoadingPhase("commit");
    setError("");
    const daSpedireRows = (preview.preview?.da_spedire as unknown[]) ?? [];
    const daMissing = daSpedireRows.length === 0;
    const needsFin = (preview.preview?.financial_review as FinancialReview | undefined)
      ?.requires_manual_review === true;
    try {
      const res = await importsApi.commitHeroesXlsx(preview.run_id, {
        categoryOverrides,
        confirmedOrderNumber: confirmedOrder || undefined,
        confirmSheetMatch: true,
        confirmImport: true,
        confirmFinancialReview: needsFin ? confirmFinancialReview : true,
        versatoOverride: versatoOverride.trim() || null,
        accontoOverrides: Object.keys(accontoOverrides).length > 0 ? accontoOverrides : null,
        openingExchangeRate: provisionRate.trim() || null,
        daSpedireSkipped: daMissing && confirmDaSpedireSkip,
      });
      navigate(`/importacoes/${res.importation_id}/resumo`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Erro ao importar";
      setError(msg);
      toast.error(msg);
      footerRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } finally {
      setLoading(false);
      setLoadingPhase("idle");
    }
  }

  async function exportNormalized(fmt: "xlsx" | "zip") {
    if (!preview) return;
    try {
      const blob = await importsApi.exportHeroesNormalized(preview.run_id, fmt);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fmt === "zip" ? "heroes-order-v1-preview.zip" : "heroes-order-v1-preview.xlsx";
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao exportar");
    }
  }

  const profileSheets = profile?.sheets ?? upload?.workbook_profile?.sheets ?? [];
  const invoiceItems = (preview?.preview?.invoice_items as Array<Record<string, unknown>>) ?? [];
  const daSpedire = (preview?.preview?.da_spedire as Array<Record<string, unknown>>) ?? [];
  const financialReview = useMemo(
    () => (preview?.preview?.financial_review ?? {}) as FinancialReview,
    [preview],
  );
  const skuTriageGroups = preview?.sku_review_groups ?? [];
  const skuOpenCount = preview?.sku_review_open_count ?? 0;
  const skuTotalCount =
    preview?.sku_review_total_count ?? skuTriageGroups.length;
  const skuResolvedCount =
    preview?.sku_review_resolved_count ??
    Math.max(0, skuTotalCount - skuOpenCount);
  const skuDraftAliases = (preview?.preview?.sku_draft_aliases as string[] | undefined) ?? [];
  const needsFinancialConfirm = financialReview.requires_manual_review === true;
  const hasDivergence = preview?.order_number_divergence ?? false;
  const daSpedireMissing = daSpedire.length === 0;
  const financialOk = !needsFinancialConfirm || confirmFinancialReview;
  const hasDraftSkus = skuDraftAliases.length > 0;
  const importWithPending = hasDraftSkus || (daSpedireMissing && confirmDaSpedireSkip);

  const commitBlocked =
    !confirmedOrder ||
    !provisionRate.trim() ||
    (preview?.errors?.length ?? 0) > 0 ||
    skuOpenCount > 0 ||
    !financialOk ||
    (hasDivergence &&
      confirmedOrder !== preview?.order_number_from_content &&
      !(confirmedOrder.length > 0));

  const commitState: Step4CommitState = commitBlocked
    ? {
        mode: "disabled",
        label: "Confirmar e importar",
        title: skuOpenCount > 0
          ? "Confirme todos os vínculos de SKU"
          : !financialOk
            ? "Confirme a revisão financeira"
            : "Preencha ordem e câmbio provisionado",
      }
    : importWithPending
      ? {
          mode: "yellow",
          label: "Importar com pendências",
          title: hasDraftSkus
            ? "Há produtos rascunho na ordem"
            : "DA SPEDIRE ausente — conferência logística incompleta",
        }
      : {
          mode: "green",
          label: "Confirmar e importar",
        };

  const currentStep = preview ? (commitBlocked ? 2 : 3) : upload ? 1 : 0;
  const STEPS = ["Carregar planilha", "Selecionar a aba", "Revisar preview", "Importar"];

  return (
    <Card>
      <PageHeader
        title="Importar planilha Heroes"
        subtitle="Carregue a planilha legada, revise o que o sistema entendeu e importe. Nada é gravado antes da sua confirmação."
      />

      <div className="ux-steps" style={{ marginBottom: "var(--space-4)" }}>
        {STEPS.map((s, i) => (
          <div key={s} className={`ux-step${i === currentStep ? " ux-step--on" : ""}${i < currentStep ? " ux-step--done" : ""}`}>
            <span className="ux-step__num">{i < currentStep ? "✓" : i + 1}</span>
            {s}
          </div>
        ))}
      </div>

      {error && !preview && (
        <div className="heroes-upload__attached-error">
          <p className="error">{error}</p>
          {attachedOrderId && error.includes("Central da ordem") && (
            <Button variant="primary" onClick={() => navigate(`/importacoes/${attachedOrderId}/resumo`)}>
              Abrir Central da ordem
            </Button>
          )}
        </div>
      )}
      {csvMsg && <p className="meta">{csvMsg}</p>}
      {locateMsg && <p className="meta">{locateMsg}</p>}

      <section className="heroes-upload__section">
        <h3>1. Planilha legada (diagnóstico)</h3>
        <p className="meta">
          Ordem de busca: <code>CONTI ITALIA-BRASILE.xlsx</code> na raiz →{" "}
          <code>data/raw/</code> → upload manual. A planilha real não é input oficial direto.
        </p>
        <div className="heroes-upload__actions">
          <Button variant="secondary" onClick={handleLoadLocal} disabled={loading}>
            Carregar da raiz / data/raw
          </Button>
          <Button variant="secondary" onClick={handleAnalyzeOnly} disabled={loading}>
            Analisar planilha (sem gravar)
          </Button>
          <input type="file" accept=".xlsx,.xlsm" onChange={handleXlsx} />
        </div>
      </section>

      <section className="heroes-upload__section">
        <h3>CSV legado (vai para a fila de revisão)</h3>
        <input type="file" accept=".csv" onChange={handleCsv} />
      </section>

      {loading && (
        <LoadingState
          label={loadingLabel()}
          detail={
            loadingPhase === "preview" && invoiceItems.length > 0
              ? `${invoiceItems.length} itens`
              : loadingPhase === "sku-sync"
                ? "atualizando vínculos"
                : undefined
          }
        />
      )}

      {profileSheets.length > 0 && (
        <section className="heroes-upload__section">
          <h3>2. Profiling da workbook ({profileSheets.length} sheets)</h3>
          <p className="meta">
            Profiling read-only — não grava no banco. Locale: it-IT.{" "}
            {profile?.note ?? upload?.workbook_profile?.note}
          </p>
          <div className="order-queue__scroll">
            <table className="sheet-table">
              <thead>
                <tr>
                  <th>Sheet</th>
                  <th>Tipo</th>
                  <th>Ordem (nome)</th>
                  <th>Ordem (conteúdo)</th>
                  <th>Conf.</th>
                  <th>Merges</th>
                  <th>Recomendação</th>
                </tr>
              </thead>
              <tbody>
                {profileSheets.map((s) => (
                  <tr
                    key={s.sheet_name}
                    className={s.order_number_divergence ? "heroes-upload__row-warn" : undefined}
                  >
                    <td>{s.sheet_name}</td>
                    <td>{s.sheet_type}</td>
                    <td>{s.order_number_from_sheet_name ?? emptyDash(null)}</td>
                    <td>{s.order_number_from_content ?? emptyDash(null)}</td>
                    <td className="num">{Number(s.parser_confidence).toFixed(2)}</td>
                    <td className="num">{s.merged_cell_count}</td>
                    <td>{s.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {upload && (
        <section className="heroes-upload__section">
          <h3>3. Selecionar sheet para preview</h3>
          {upload.source_path && <p className="meta">Fonte: {upload.source_path}</p>}
          <select value={selectedSheet} onChange={(e) => setSelectedSheet(e.target.value)}>
            <option value="">— Selecione a aba —</option>
            {upload.sheets.map((s) => (
              <option key={s.sheet_name} value={s.sheet_name}>
                {s.sheet_name} — {s.sheet_type}
                {s.order_number_hint ? ` (ordine ${s.order_number_hint})` : ""}
                {s.order_number_divergence ? " ⚠ divergência" : ""}
              </option>
            ))}
          </select>
          <Button variant="secondary" onClick={loadPreview} disabled={!selectedSheet || loading}>
            Gerar preview normalizado
          </Button>
        </section>
      )}

      {preview && (
        <HeroesUploadStep4Layout
          preview={preview}
          confirmedOrder={confirmedOrder}
          onConfirmedOrderChange={setConfirmedOrder}
          provisionRate={provisionRate}
          onProvisionRateChange={setProvisionRate}
          financialReview={financialReview}
          versatoOverride={versatoOverride}
          onVersatoOverrideChange={setVersatoOverride}
          accontoOverrides={accontoOverrides}
          onAccontoOverrideChange={(inv, value) =>
            setAccontoOverrides((prev) => ({ ...prev, [inv]: value }))
          }
          confirmFinancialReview={confirmFinancialReview}
          onConfirmFinancialReviewChange={setConfirmFinancialReview}
          skuTriageGroups={skuTriageGroups}
          skuOpenCount={skuOpenCount}
          skuResolvedCount={skuResolvedCount}
          skuTotalCount={skuTotalCount}
          skuDraftAliases={skuDraftAliases}
          onSkuResolved={() => loadPreview(true)}
          confirmDaSpedireSkip={confirmDaSpedireSkip}
          onConfirmDaSpedireSkipChange={setConfirmDaSpedireSkip}
          categoryOverrides={categoryOverrides}
          onCategoryOverrideChange={(name, cat) =>
            setCategoryOverrides((o) => ({ ...o, [name]: cat }))
          }
          invoicePage={invoicePage}
          onInvoicePageChange={setInvoicePage}
          commitState={commitState}
          onCommit={commitImport}
          onExportXlsx={() => exportNormalized("xlsx")}
          onExportZip={() => exportNormalized("zip")}
          loading={loading}
          error={error}
          footerRef={footerRef}
          hasDivergence={hasDivergence}
        />
      )}
    </Card>
  );
}
