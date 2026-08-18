import { Link, useLocation, useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { User } from "../auth/types";
import { listUsers, type UserAdmin } from "./identityApi";
import { useListReturn } from "../../navigation/useListReturn";
import { saveReturnState } from "../../navigation/returnState";
import {
  EmptyState,
  ErrorState,
  FilterBar,
  LoadingState,
  OperationalTable,
  PageHeader,
  PaginationSummary,
  TextInput,
  roleLabel,
  type OperationalColumnDef,
} from "../../ui";

type Props = { user: User };
const PAGE = 50;

function canRead(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("users:read");
}

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("users:write");
}

export function UsersListPage({ user }: Props) {
  const location = useLocation();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const offset = Number(params.get("offset") || "0") || 0;
  const [rows, setRows] = useState<UserAdmin[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(params.get("row") || null);
  const [draftQ, setDraftQ] = useState(q);

  useListReturn("/admin/users", selectedId);
  useEffect(() => setDraftQ(q), [q]);

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    void listUsers({ q: q || undefined, limit: PAGE, offset })
      .then((data) => {
        if (!cancelled) {
          setRows(data.items);
          setTotal(data.total);
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      });
    return () => {
      cancelled = true;
    };
  }, [q, offset]);

  const rememberRow = useCallback(
    (id: number) => {
      setSelectedId(String(id));
      saveReturnState("/admin/users", {
        search: location.search,
        scrollY: window.scrollY,
        selectedId: String(id),
      });
    },
    [location.search],
  );

  const returnTo = `${location.pathname}${location.search}`;
  const columns = useMemo(
    (): OperationalColumnDef<UserAdmin>[] => [
      {
        id: "name",
        header: "Nome",
        visibility: "always",
        priority: 0,
        minWidth: "10rem",
        truncate: true,
        cell: (row) => (
          <Link to={`/admin/users/${row.id}`} state={{ returnTo }} onClick={() => rememberRow(row.id)}>
            {row.name}
          </Link>
        ),
      },
      {
        id: "email",
        header: "E-mail",
        visibility: "always",
        priority: 0,
        minWidth: "12rem",
        truncate: true,
        cell: (row) => row.email,
      },
      {
        id: "role",
        header: "Papel",
        visibility: "always",
        priority: 0,
        minWidth: "8rem",
        cell: (row) => roleLabel(row.role),
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

  if (!canRead(user)) {
    return <ErrorState message="Sem permissão para usuários." />;
  }
  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState message="Carregando usuários…" />;

  return (
    <section className="panel dense" data-testid="users-list-page">
      <PageHeader
        title="Usuários"
        subtitle="Acesso e papéis"
        actions={
          canWrite(user) ? (
            <Link className="ui-button" to="/admin/users/new" data-testid="users-new-cta">
              Novo usuário
            </Link>
          ) : null
        }
      />
      <FilterBar
        primary={
          <form
            className="stack-row"
            onSubmit={(e) => {
              e.preventDefault();
              const next = new URLSearchParams(params);
              if (!draftQ.trim()) next.delete("q");
              else next.set("q", draftQ.trim());
              next.delete("offset");
              setParams(next);
            }}
          >
            <TextInput
              data-testid="users-search"
              value={draftQ}
              onChange={(e) => setDraftQ(e.target.value)}
              placeholder="Buscar nome ou e-mail"
              aria-label="Buscar usuários"
            />
          </form>
        }
      />
      {rows.length === 0 ? (
        <EmptyState
          title={q ? "Nenhum resultado" : "Nenhum usuário"}
          message={q ? "Nenhum usuário neste filtro" : "Crie o primeiro usuário."}
        />
      ) : (
        <>
          <OperationalTable
            density="standard"
            data-testid="users-table"
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
