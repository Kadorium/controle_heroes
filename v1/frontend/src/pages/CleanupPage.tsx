import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { importsApi, type CancelledSummaryResponse } from "../api";
import { Button, Card, EmptyState, LoadingState, PageHeader, useToast } from "../components";
import { statusLabel } from "../i18n/glossario";
import { fmtDate } from "../utils/formatDate";

type EntityKind = "importations" | "products" | "suppliers";

/** Compatível com respostas antigas que usavam *_sample em vez de listas completas. */
function normalizeCancelledSummary(raw: CancelledSummaryResponse): CancelledSummaryResponse {
  const legacy = raw as CancelledSummaryResponse & {
    products_cancelled_sample?: CancelledSummaryResponse["products"];
    suppliers_cancelled_sample?: CancelledSummaryResponse["suppliers"];
  };
  return {
    ...raw,
    importations: raw.importations ?? [],
    products: raw.products ?? legacy.products_cancelled_sample ?? [],
    suppliers: raw.suppliers ?? legacy.suppliers_cancelled_sample ?? [],
  };
}

type Selection = Record<EntityKind, Set<number>>;

const EMPTY_SELECTION: Selection = {
  importations: new Set(),
  products: new Set(),
  suppliers: new Set(),
};

export function CleanupPage() {
  const toast = useToast();
  const [data, setData] = useState<CancelledSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Selection>(EMPTY_SELECTION);
  const [confirmPermanent, setConfirmPermanent] = useState(false);
  const [purging, setPurging] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const summary = normalizeCancelledSummary(await importsApi.cancelledSummary());
      setData(summary);
      setSelected(EMPTY_SELECTION);
      setConfirmPermanent(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar resumo");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const totalSelected = useMemo(
    () => selected.importations.size + selected.products.size + selected.suppliers.size,
    [selected],
  );

  const orphanArtifactCount = useMemo(() => {
    if (!data) return 0;
    return (
      data.counts.staging_rows +
      data.counts.heroes_runs_orphan +
      data.counts.raw_files_orphan
    );
  }, [data]);

  const hasInactiveRecords = useMemo(() => {
    if (!data) return false;
    return (
      data.importations.length > 0 ||
      data.products.length > 0 ||
      data.suppliers.length > 0 ||
      orphanArtifactCount > 0
    );
  }, [data, orphanArtifactCount]);

  const actionsEnabled = Boolean(data?.purge_allowed && confirmPermanent && !purging);

  function toggle(kind: EntityKind, id: number) {
    setSelected((prev) => {
      const next = new Set(prev[kind]);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return { ...prev, [kind]: next };
    });
  }

  function toggleAll(kind: EntityKind, ids: number[]) {
    setSelected((prev) => {
      const allOn = ids.length > 0 && ids.every((id) => prev[kind].has(id));
      return { ...prev, [kind]: allOn ? new Set() : new Set(ids) };
    });
  }

  async function runPurgeSelected() {
    if (!data?.purge_allowed) {
      toast.error(data?.purge_block_reason ?? "Exclusão permanente não permitida neste ambiente");
      return;
    }
    if (totalSelected === 0) {
      toast.error("Selecione ao menos um registro");
      return;
    }
    if (!confirmPermanent) return;

    setPurging(true);
    try {
      const result = await importsApi.purgeCancelled({
        importation_ids: selected.importations.size ? [...selected.importations] : undefined,
        product_ids: selected.products.size ? [...selected.products] : undefined,
        supplier_ids: selected.suppliers.size ? [...selected.suppliers] : undefined,
      });
      const parts = [
        result.importations_removed > 0 ? `${result.importations_removed} ordem(ns)` : null,
        (result.products_removed ?? 0) > 0 ? `${result.products_removed} produto(s)` : null,
        (result.suppliers_removed ?? 0) > 0 ? `${result.suppliers_removed} fornecedor(es)` : null,
      ].filter(Boolean);
      toast.success(parts.length ? `Removido: ${parts.join(", ")}` : "Nada a remover");
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Falha na exclusão");
    } finally {
      setPurging(false);
    }
  }

  async function runPurgeOrphans() {
    if (!data?.purge_allowed || !confirmPermanent) return;
    setPurging(true);
    try {
      const result = await importsApi.purgeCancelled({ purge_orphan_artifacts: true });
      const parts = [
        (result.staging_rows_removed ?? 0) > 0 ? `${result.staging_rows_removed} staging` : null,
        (result.heroes_runs_removed ?? 0) > 0 ? `${result.heroes_runs_removed} runs Heroes` : null,
        (result.raw_files_removed ?? 0) > 0 ? `${result.raw_files_removed} arquivos raw` : null,
      ].filter(Boolean);
      toast.success(parts.length ? `Removido: ${parts.join(", ")}` : "Nada a remover");
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Falha na exclusão");
    } finally {
      setPurging(false);
    }
  }

  async function runPurgeAllCancelled(kind: "importations" | "products" | "suppliers") {
    if (!data?.purge_allowed || !confirmPermanent) return;
    setPurging(true);
    try {
      const payload =
        kind === "importations"
          ? { purge_all_cancelled_importations: true }
          : kind === "products"
            ? { purge_all_cancelled_products: true }
            : { purge_all_cancelled_suppliers: true };
      const result = await importsApi.purgeCancelled(payload);
      const parts = [
        result.importations_removed > 0 ? `${result.importations_removed} ordem(ns)` : null,
        (result.products_removed ?? 0) > 0 ? `${result.products_removed} produto(s)` : null,
        (result.suppliers_removed ?? 0) > 0 ? `${result.suppliers_removed} fornecedor(es)` : null,
      ].filter(Boolean);
      toast.success(parts.length ? `Removido: ${parts.join(", ")}` : "Nada a remover");
      await load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Falha na exclusão");
    } finally {
      setPurging(false);
    }
  }

  if (loading) return <LoadingState label="Carregando registros inativos..." />;

  return (
    <Card>
      <PageHeader
        title="Registros inativos"
        subtitle="Cadastros anulados permanecem no banco até exclusão definitiva. Selecione o que deseja remover — ordens devem ser excluídas antes de produtos ou fornecedores ainda referenciados."
        actions={
          <Button variant="ghost" onClick={() => void load()} disabled={purging}>
            Atualizar
          </Button>
        }
      />

      {error && <p className="error">{error}</p>}

      {data && !data.purge_allowed && (
        <div className="cleanup-page__notice meta" role="status">
          <strong>Exclusão permanente bloqueada.</strong> {data.purge_block_reason}
        </div>
      )}

      {data && (
        <>
          <div className="cleanup-page__stats">
            <Stat label="Ordens anuladas" value={data.counts.importations_cancelled} />
            <Stat label="Produtos anulados" value={data.counts.products_cancelled} />
            <Stat label="Fornecedores anulados" value={data.counts.suppliers_cancelled} />
            <Stat label="Runs Heroes órfãos" value={data.counts.heroes_runs_orphan} />
            <Stat label="Linhas staging" value={data.counts.staging_rows} />
            <Stat label="Arquivos raw órfãos" value={data.counts.raw_files_orphan} />
          </div>

          <div className="cleanup-page__toolbar">
            <label className="cleanup-page__confirm">
              <input
                type="checkbox"
                checked={confirmPermanent}
                onChange={(e) => setConfirmPermanent(e.target.checked)}
                disabled={purging}
              />
              <span>
                Confirmo exclusão permanente. Esta ação não pode ser desfeita.
              </span>
            </label>

            <div className="cleanup-page__actions">
              <Button
                variant="danger"
                disabled={!actionsEnabled || totalSelected === 0}
                loading={purging}
                onClick={() => void runPurgeSelected()}
              >
                Excluir selecionados ({totalSelected})
              </Button>

              {data.counts.importations_cancelled > 0 && (
                <Button
                  variant="secondary"
                  disabled={!actionsEnabled}
                  loading={purging}
                  onClick={() => void runPurgeAllCancelled("importations")}
                >
                  Excluir todas as ordens ({data.counts.importations_cancelled})
                </Button>
              )}

              {data.counts.products_cancelled > 0 && (
                <Button
                  variant="secondary"
                  disabled={!actionsEnabled}
                  loading={purging}
                  onClick={() => void runPurgeAllCancelled("products")}
                >
                  Excluir todos os produtos ({data.counts.products_cancelled})
                </Button>
              )}

              {data.counts.suppliers_cancelled > 0 && (
                <Button
                  variant="secondary"
                  disabled={!actionsEnabled}
                  loading={purging}
                  onClick={() => void runPurgeAllCancelled("suppliers")}
                >
                  Excluir todos os fornecedores ({data.counts.suppliers_cancelled})
                </Button>
              )}

              <Button
                variant="danger"
                disabled={!actionsEnabled || orphanArtifactCount === 0}
                loading={purging}
                onClick={() => void runPurgeOrphans()}
              >
                Excluir todos os artefatos órfãos ({orphanArtifactCount})
              </Button>
            </div>

            {!data.purge_allowed && (
              <p className="meta">Marque a confirmação acima quando a exclusão estiver liberada.</p>
            )}
          </div>

          <EntitySection
            title="Ordens de importação"
            empty="Nenhuma ordem anulada"
            rows={data.importations}
            selected={selected.importations}
            onToggle={(id) => toggle("importations", id)}
            onToggleAll={() => toggleAll("importations", data.importations.map((r) => r.id))}
            columns={["PO", "Fornecedor", "Status", "Anulada em", "Motivo"]}
            renderRow={(row) => (
              <>
                <td>
                  <Link to={`/importacoes/${row.id}/resumo`}>{row.po_number}</Link>
                </td>
                <td>{row.supplier_name ?? "—"}</td>
                <td>{statusLabel(row.current_status)}</td>
                <td>{row.cancelled_at ? fmtDate(row.cancelled_at) : "—"}</td>
                <td className="cleanup-page__reason">{row.cancellation_reason ?? "—"}</td>
              </>
            )}
          />

          <EntitySection
            title="Produtos"
            empty="Nenhum produto anulado"
            rows={data.products}
            selected={selected.products}
            onToggle={(id) => toggle("products", id)}
            onToggleAll={() => toggleAll("products", data.products.map((r) => r.id))}
            columns={["SKU", "Descrição", "Anulado em", "Motivo"]}
            renderRow={(row) => (
              <>
                <td>
                  <Link to={`/cadastros/produtos/${row.id}`}>{row.sku_code}</Link>
                </td>
                <td>{row.description}</td>
                <td>{row.cancelled_at ? fmtDate(row.cancelled_at) : "—"}</td>
                <td className="cleanup-page__reason">{row.cancellation_reason ?? "—"}</td>
              </>
            )}
          />

          <EntitySection
            title="Fornecedores"
            empty="Nenhum fornecedor anulado"
            rows={data.suppliers}
            selected={selected.suppliers}
            onToggle={(id) => toggle("suppliers", id)}
            onToggleAll={() => toggleAll("suppliers", data.suppliers.map((r) => r.id))}
            columns={["Nome", "País", "Anulado em", "Motivo"]}
            renderRow={(row) => (
              <>
                <td>{row.name}</td>
                <td>{row.country ?? "—"}</td>
                <td>{row.cancelled_at ? fmtDate(row.cancelled_at) : "—"}</td>
                <td className="cleanup-page__reason">{row.cancellation_reason ?? "—"}</td>
              </>
            )}
          />

          {!hasInactiveRecords && (
            <p className="meta cleanup-page__empty-hint">Nenhum cadastro inativo no momento.</p>
          )}
        </>
      )}
    </Card>
  );
}

function EntitySection<T extends { id: number }>({
  title,
  empty,
  rows,
  selected,
  onToggle,
  onToggleAll,
  columns,
  renderRow,
}: {
  title: string;
  empty: string;
  rows: T[];
  selected: Set<number>;
  onToggle: (id: number) => void;
  onToggleAll: () => void;
  columns: string[];
  renderRow: (row: T) => ReactNode;
}) {
  const allSelected = rows.length > 0 && rows.every((r) => selected.has(r.id));

  return (
    <section className="cleanup-page__section">
      <h2>{title}</h2>
      {rows.length === 0 ? (
        <EmptyState title={empty} />
      ) : (
        <div className="order-queue__scroll">
          <table className="sheet-table">
            <thead>
              <tr>
                <th>
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={onToggleAll}
                    aria-label={`Selecionar todos — ${title}`}
                  />
                </th>
                {columns.map((c) => (
                  <th key={c}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={selected.has(row.id)}
                      onChange={() => onToggle(row.id)}
                      aria-label={`Selecionar ${row.id}`}
                    />
                  </td>
                  {renderRow(row)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="cleanup-page__stat">
      <span className="cleanup-page__stat-value">{value}</span>
      <span className="cleanup-page__stat-label">{label}</span>
    </div>
  );
}
