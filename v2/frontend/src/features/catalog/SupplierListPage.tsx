import { Link, useLocation, useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { User } from "../auth/types";
import { fetchSupplierList, type Supplier } from "./catalogApi";
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

export function SupplierListPage({ user }: Props) {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const active = params.get("active") ?? "";
  const missingTax = params.get("missing_tax") === "1";
  const sort = params.get("sort") || "name";
  const offset = Number(params.get("offset") || "0") || 0;
  const [rows, setRows] = useState<Supplier[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(params.get("row") || null);
  const [draftQ, setDraftQ] = useState(q);

  useListReturn("/catalog/suppliers", selectedId);

  useEffect(() => setDraftQ(q), [q]);

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    void (async () => {
      try {
        const data = await fetchSupplierList({
          q: q || undefined,
          activeOnly: active === "1",
          missingTaxId: missingTax,
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
  }, [q, active, missingTax, sort, offset]);

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (!value) next.delete(key);
    else next.set(key, value);
    next.delete("offset");
    setParams(next);
  }

  const rememberRow = useCallback(
    (id: number) => {
      setSelectedId(String(id));
      saveReturnState("/catalog/suppliers", {
        search: location.search,
        scrollY: window.scrollY,
        selectedId: String(id),
      });
    },
    [location.search],
  );

  const returnTo = `${location.pathname}${location.search}`;
  const columns = useMemo(
    (): OperationalColumnDef<Supplier>[] => [
      {
        id: "name",
        header: "Nome",
        visibility: "always",
        priority: 0,
        minWidth: "12rem",
        truncate: true,
        cell: (row) => (
          <Link
            to={`/catalog/suppliers/${row.id}`}
            state={{ returnTo }}
            onClick={() => rememberRow(row.id)}
          >
            {row.name}
          </Link>
        ),
      },
      {
        id: "code",
        header: "Código",
        visibility: "standard",
        priority: 1,
        minWidth: "7rem",
        cell: (row) => row.code || "—",
      },
      {
        id: "tax",
        header: "Identificador fiscal",
        visibility: "standard",
        priority: 1,
        minWidth: "8rem",
        cell: (row) => row.tax_id || "—",
      },
      {
        id: "country",
        header: "País",
        visibility: "standard",
        priority: 1,
        minWidth: "4rem",
        cell: (row) => row.country_code || "—",
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

  const hasQuery = Boolean(q || active || missingTax);
  const activeFilters = [
    q ? { id: "q", label: `Busca: ${q}`, onRemove: () => setParam("q", "") } : null,
    active === "1" ? { id: "active", label: "Só ativos", onRemove: () => setParam("active", "") } : null,
    missingTax
      ? { id: "tax", label: "Sem identificador fiscal", onRemove: () => setParam("missing_tax", "") }
      : null,
  ].filter(Boolean) as { id: string; label: string; onRemove: () => void }[];

  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState message="Carregando fornecedores…" />;

  return (
    <section className="panel dense" data-testid="supplier-list-page">
      <PageHeader
        title="Fornecedores"
        subtitle="Cadastro comercial"
        actions={
          canWrite(user) ? (
            <Link className="ui-button" to="/catalog/suppliers/new" data-testid="suppliers-new-cta">
              Novo fornecedor
            </Link>
          ) : null
        }
      />
      <FilterBar
        primary={
          <form
            className="stack-row"
            style={{ flexWrap: "wrap", gap: "0.75rem" }}
            onSubmit={(e) => {
              e.preventDefault();
              setParam("q", draftQ.trim());
            }}
          >
            <TextInput
              data-testid="suppliers-search"
              value={draftQ}
              onChange={(e) => setDraftQ(e.target.value)}
              placeholder="Buscar nome, código ou identificador"
              aria-label="Buscar fornecedores"
            />
            <Button type="submit" variant="secondary" data-testid="suppliers-search-submit">
              Buscar
            </Button>
            <FilterChip
              pressed={active === "1"}
              data-testid="suppliers-filter-active"
              onClick={() => setParam("active", active === "1" ? "" : "1")}
            >
              Só ativos
            </FilterChip>
            <FilterChip
              pressed={missingTax}
              data-testid="suppliers-filter-tax"
              onClick={() => setParam("missing_tax", missingTax ? "" : "1")}
            >
              Sem identificador fiscal
            </FilterChip>
          </form>
        }
        activeFilters={activeFilters}
        onClearAll={hasQuery ? () => setParams(new URLSearchParams()) : undefined}
      />
      {rows.length === 0 && !hasQuery ? (
        <EmptyState title="Nenhum fornecedor" message="Cadastre o primeiro fornecedor." />
      ) : rows.length === 0 ? (
        <EmptyState
          title="Nenhum resultado"
          message="Nenhum fornecedor neste filtro"
          orientation="Ajuste a busca ou limpe os filtros."
        />
      ) : (
        <>
          <OperationalTable
            density="standard"
            data-testid="suppliers-table"
            columns={columns}
            rows={rows}
            getRowId={(row) => String(row.id)}
            selectedId={selectedId}
            onRowClick={(row) => rememberRow(row.id)}
          />
          <PaginationSummary offset={offset} limit={PAGE} total={total} loadedCount={rows.length} />
        </>
      )}
    </section>
  );
}
