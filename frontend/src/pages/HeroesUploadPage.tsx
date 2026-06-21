import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  importsApi,
  type HeroesWorkbookProfileResponse,
  type HeroesXlsxPreviewResponse,
  type HeroesXlsxUploadResponse,
} from "../api";
import { Button, Card, LoadingState, PageHeader } from "../components";
import { emptyDash, productCategoryLabel } from "../i18n/glossario";

const CATEGORY_OPTIONS = ["RACKET", "BALL", "BAG_ACCESSORY", "APPAREL", "PICKLEBALL", "OTHER"] as const;

export function HeroesUploadPage() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [locateMsg, setLocateMsg] = useState("");
  const [upload, setUpload] = useState<HeroesXlsxUploadResponse | null>(null);
  const [profile, setProfile] = useState<HeroesWorkbookProfileResponse | null>(null);
  const [selectedSheet, setSelectedSheet] = useState("");
  const [preview, setPreview] = useState<HeroesXlsxPreviewResponse | null>(null);
  const [categoryOverrides, setCategoryOverrides] = useState<Record<string, string>>({});
  const [confirmedOrder, setConfirmedOrder] = useState("");
  const [confirmSheet, setConfirmSheet] = useState(false);
  const [confirmImport, setConfirmImport] = useState(false);
  const [csvMsg, setCsvMsg] = useState("");

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
      setError(err instanceof Error ? err.message : "Erro no profiling");
    } finally {
      setLoading(false);
    }
  }

  function applyUpload(res: HeroesXlsxUploadResponse) {
    setUpload(res);
    setProfile(res.workbook_profile ?? null);
    const orderSheet =
      res.workbook_profile?.sheets.find((s) => s.recommendation === "importar") ??
      res.sheets.find((s) => s.sheet_type === "ORDER") ??
      res.sheets[0];
    if (orderSheet) {
      const name = "sheet_name" in orderSheet ? orderSheet.sheet_name : orderSheet.sheet_name;
      setSelectedSheet(name);
      const ord =
        ("order_number_from_content" in orderSheet && orderSheet.order_number_from_content) ||
        orderSheet.order_number_hint ||
        "";
      setConfirmedOrder(String(ord));
    }
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
      setCsvMsg(`CSV importado: ${result.row_count ?? 0} linhas para staging.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro CSV");
    }
  }

  async function loadPreview() {
    if (!upload || !selectedSheet) return;
    setLoading(true);
    setError("");
    try {
      const p = await importsApi.previewHeroesXlsx(
        upload.raw_file_id,
        selectedSheet,
        confirmedOrder || undefined,
      );
      setPreview(p);
      if (!confirmedOrder && p.order_number) setConfirmedOrder(p.order_number);
      if (p.already_committed && p.importation_id) {
        navigate(`/importacoes/${p.importation_id}/resumo`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro no preview");
    } finally {
      setLoading(false);
    }
  }

  async function commitImport() {
    if (!preview) return;
    setLoading(true);
    setError("");
    try {
      const res = await importsApi.commitHeroesXlsx(preview.run_id, {
        categoryOverrides,
        confirmedOrderNumber: confirmedOrder || undefined,
        confirmSheetMatch: confirmSheet,
        confirmImport,
      });
      navigate(`/importacoes/${res.importation_id}/resumo`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao importar");
    } finally {
      setLoading(false);
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
  const newProducts = (preview?.preview?.new_products as Array<Record<string, unknown>>) ?? [];
  const hasDivergence = preview?.order_number_divergence ?? false;
  const canCommit =
    confirmSheet &&
    confirmImport &&
    !!confirmedOrder &&
    (preview?.errors?.length ?? 0) === 0 &&
    (!hasDivergence || confirmedOrder === preview?.order_number_from_content || confirmedOrder.length > 0);

  return (
    <Card>
      <PageHeader
        title="Importação Heroes (XLSX/CSV)"
        subtitle="Planilha legada CONTI ITALIA-BRASILE — profiling e preview obrigatórios. Contrato oficial: Heroes Order Import Format v1."
      />

      {error && <p className="error">{error}</p>}
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
            Analisar planilha (profiling)
          </Button>
          <input type="file" accept=".xlsx,.xlsm" onChange={handleXlsx} />
        </div>
      </section>

      <section className="heroes-upload__section">
        <h3>CSV legado (staging)</h3>
        <input type="file" accept=".csv" onChange={handleCsv} />
      </section>

      {loading && <LoadingState label="Processando planilha..." />}

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
        <section className="heroes-upload__section heroes-upload__preview">
          <h3>4. Preview — Heroes Order v1</h3>
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

          <label>
            Confirmar número da ordem:{" "}
            <input
              value={confirmedOrder}
              onChange={(e) => setConfirmedOrder(e.target.value)}
              placeholder={preview.order_number ?? "ex.: 758"}
            />
          </label>

          <p className="order-queue__meta">
            {invoiceItems.length} itens fatura · {daSpedire.length} linhas DA SPEDIRE ·{" "}
            {newProducts.length} produtos
          </p>

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
                            onChange={(e) =>
                              setCategoryOverrides((o) => ({ ...o, [name]: e.target.value }))
                            }
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

          <div className="order-queue__scroll">
            <table className="sheet-table">
              <thead>
                <tr>
                  <th>Fatura</th>
                  <th>Data</th>
                  <th>Produto / Modelo</th>
                  <th className="num">Qtd</th>
                  <th className="num">Acconto</th>
                </tr>
              </thead>
              <tbody>
                {invoiceItems.slice(0, 50).map((row, i) => (
                  <tr key={i}>
                    <td>{String(row.invoice_number ?? emptyDash(null))}</td>
                    <td>{String(row.invoice_date ?? emptyDash(null))}</td>
                    <td>{String(row.product_name_raw)}</td>
                    <td className="num">{String(row.item_quantity ?? emptyDash(null))}</td>
                    <td className="num">{String(row.acconto_amount ?? emptyDash(null))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="heroes-upload__actions">
            <Button variant="secondary" onClick={() => exportNormalized("xlsx")}>
              Baixar preview XLSX (v1)
            </Button>
            <Button variant="secondary" onClick={() => exportNormalized("zip")}>
              Exportar CSVs (ZIP)
            </Button>
          </div>

          <div className="heroes-upload__confirm">
            <label>
              <input type="checkbox" checked={confirmSheet} onChange={(e) => setConfirmSheet(e.target.checked)} />
              Confirmo que a sheet selecionada está correta
            </label>
            <label>
              <input type="checkbox" checked={confirmImport} onChange={(e) => setConfirmImport(e.target.checked)} />
              Confirmo importação após revisão do preview
            </label>
          </div>

          <Button onClick={commitImport} disabled={loading || !canCommit}>
            Importar ordem (commit)
          </Button>
        </section>
      )}
    </Card>
  );
}
