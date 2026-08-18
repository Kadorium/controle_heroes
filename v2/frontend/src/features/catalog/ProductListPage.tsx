import { Link, useLocation, useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { User } from "../auth/types";
import { fetchProductList, type Product } from "./catalogApi";
import { useListReturn } from "../../navigation/useListReturn";
import { saveReturnState } from "../../navigation/returnState";
import {
  Button,
  EmptyState,
  ErrorState,
  FilterBar,
  FilterChip,
  LoadingState,
  OperationalTable,
  PageHeader,
  PaginationSummary,
  TextInput,
  type OperationalColumnDef,
} from "../../ui";

type Props = { user: User };

const PAGE = 50;

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("catalog:write");
}

export function ProductListPage({ user }: Props) {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const active = params.get("active") ?? "";
  const incomplete = params.get("incomplete") === "1";
  const missingNcm = params.get("missing_ncm") === "1";
  const size = params.get("size") ?? "";
  const color = params.get("color") ?? "";
  const sort = params.get("sort") || "sku";
  const offset = Number(params.get("offset") || "0") || 0;
  const [rows, setRows] = useState<Product[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(params.get("row") || null);
  const [draftQ, setDraftQ] = useState(q);

  useListReturn("/catalog/products", selectedId);

  useEffect(() => {
    setDraftQ(q);
  }, [q]);

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    void (async () => {
      try {
        const data = await fetchProductList({
          q: q || undefined,
          activeOnly: active === "1",
          incomplete,
          missingNcm,
          size: size || undefined,
          color: color || undefined,
          sort,
          limit: PAGE,
          offset,
        });
        if (!cancelled) {
          setRows(data.items);
          setTotal(data.total);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [q, active, incomplete, missingNcm, size, color, sort, offset]);

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (!value) next.delete(key);
    else next.set(key, value);
    next.delete("offset");
    setParams(next);
  }

  function applySearch() {
    setParam("q", draftQ.trim());
  }

  const rememberRow = useCallback(
    (id: number) => {
      setSelectedId(String(id));
      saveReturnState("/catalog/products", {
        search: location.search,
        scrollY: window.scrollY,
        selectedId: String(id),
      });
    },
    [location.search],
  );

  const returnTo = `${location.pathname}${location.search}`;
  const columns = useMemo(
    (): OperationalColumnDef<Product>[] => [
      {
        id: "sku",
        header: "SKU",
        visibility: "always",
        priority: 0,
        minWidth: "8rem",
        truncate: true,
        cell: (row) => (
          <Link
            to={`/catalog/products/${row.id}`}
            state={{ returnTo }}
            onClick={() => rememberRow(row.id)}
          >
            {row.sku}
          </Link>
        ),
      },
      {
        id: "description",
        header: "Descrição",
        visibility: "always",
        priority: 0,
        minWidth: "12rem",
        truncate: true,
        cell: (row) => row.description,
      },
      {
        id: "ncm",
        header: "NCM",
        visibility: "standard",
        priority: 1,
        minWidth: "6rem",
        cell: (row) => row.ncm || "—",
      },
      {
        id: "active",
        header: "Ativo",
        visibility: "always",
        priority: 0,
        minWidth: "5rem",
        cell: (row) => (row.is_active ? "Sim" : "Não"),
      },
    ],
    [rememberRow, returnTo],
  );

  const hasQuery = Boolean(q || active || incomplete || missingNcm || size || color);
  const activeFilters = [
    q ? { id: "q", label: `Busca: ${q}`, onRemove: () => setParam("q", "") } : null,
    active === "1" ? { id: "active", label: "Só ativos", onRemove: () => setParam("active", "") } : null,
    incomplete
      ? { id: "incomplete", label: "Dados incompletos", onRemove: () => setParam("incomplete", "") }
      : null,
    missingNcm ? { id: "ncm", label: "Sem NCM", onRemove: () => setParam("missing_ncm", "") } : null,
    size ? { id: "size", label: `Tamanho: ${size}`, onRemove: () => setParam("size", "") } : null,
    color ? { id: "color", label: `Cor: ${color}`, onRemove: () => setParam("color", "") } : null,
  ].filter(Boolean) as { id: string; label: string; onRemove: () => void }[];

  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState message="Carregando produtos…" />;

  const emptyCatalog = rows.length === 0 && !hasQuery && offset === 0;
  const noResults = rows.length === 0 && hasQuery;

  return (
    <section className="panel dense" data-testid="product-list-page">
      <PageHeader
        title="Produtos"
        subtitle="Cadastro mestre de SKU"
        actions={
          canWrite(user) ? (
            <Link className="ui-button" to="/catalog/products/new" data-testid="products-new-cta">
              Novo produto
            </Link>
          ) : null
        }
      />
      <div className="queue-shell">
        <FilterBar
          primary={
            <form
              className="stack-row"
              style={{ flexWrap: "wrap", gap: "0.75rem" }}
              onSubmit={(e) => {
                e.preventDefault();
                applySearch();
              }}
            >
              <TextInput
                data-testid="products-search"
                value={draftQ}
                onChange={(e) => setDraftQ(e.target.value)}
                placeholder="Buscar SKU ou descrição"
                aria-label="Buscar produtos"
              />
              <Button type="submit" variant="secondary" data-testid="products-search-submit">
                Buscar
              </Button>
              <FilterChip
                pressed={active === "1"}
                data-testid="products-filter-active"
                onClick={() => setParam("active", active === "1" ? "" : "1")}
              >
                Só ativos
              </FilterChip>
              <FilterChip
                pressed={incomplete}
                data-testid="products-filter-incomplete"
                onClick={() => setParam("incomplete", incomplete ? "" : "1")}
              >
                Dados incompletos
              </FilterChip>
              <FilterChip
                pressed={missingNcm}
                data-testid="products-filter-ncm"
                onClick={() => setParam("missing_ncm", missingNcm ? "" : "1")}
              >
                Sem NCM
              </FilterChip>
            </form>
          }
          secondary={
            <div className="stack-row" style={{ flexWrap: "wrap", gap: "0.75rem" }}>
              <TextInput
                data-testid="products-filter-size"
                value={size}
                onChange={(e) => setParam("size", e.target.value)}
                placeholder="Tamanho"
                aria-label="Filtrar por tamanho"
              />
              <TextInput
                data-testid="products-filter-color"
                value={color}
                onChange={(e) => setParam("color", e.target.value)}
                placeholder="Cor"
                aria-label="Filtrar por cor"
              />
            </div>
          }
          activeFilters={activeFilters}
          onClearAll={hasQuery ? () => setParams(new URLSearchParams()) : undefined}
        />
      </div>
      {emptyCatalog ? (
        <EmptyState
          title="Nenhum produto"
          message="Cadastre o primeiro SKU para usá-lo nos pedidos."
        />
      ) : noResults ? (
        <EmptyState
          title="Nenhum resultado"
          message="Nenhum produto neste filtro"
          orientation="Ajuste a busca ou limpe os filtros."
        />
      ) : (
        <>
          <OperationalTable
            density="standard"
            data-testid="products-table"
            columns={columns}
            rows={rows}
            getRowId={(row) => String(row.id)}
            selectedId={selectedId}
            onRowClick={(row) => rememberRow(row.id)}
          />
          <PaginationSummary offset={offset} limit={PAGE} total={total} loadedCount={rows.length} />
          {offset + PAGE < total ? (
            <button
              type="button"
              className="ui-button ui-button--secondary"
              data-testid="products-next-page"
              onClick={() => {
                const next = new URLSearchParams(params);
                next.set("offset", String(offset + PAGE));
                setParams(next);
              }}
            >
              Próxima página
            </button>
          ) : null}
        </>
      )}
    </section>
  );
}
