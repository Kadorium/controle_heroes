import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { User } from "../auth/types";
import { listRoles, listUsers, type RoleOut, type UserAdmin } from "./identityApi";
import { useListReturn } from "../../navigation/useListReturn";
import { saveReturnState } from "../../navigation/returnState";
import {
  EmptyState,
  ErrorState,
  FilterBar,
  FilterChip,
  LoadingState,
  OperationalTable,
  PageHeader,
  PaginationSummary,
  TextInput,
  formatDateTime,
  roleLabel,
  type OperationalColumnDef,
} from "../../ui";

type Props = { user: User };
const PAGE = 50;
const DEBOUNCE_MS = 280;

function canRead(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("users:read");
}

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("users:write");
}

export function UsersListPage({ user }: Props) {
  const location = useLocation();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const active = params.get("active") ?? "";
  const role = params.get("role") ?? "";
  const offset = Number(params.get("offset") || "0") || 0;
  const [rows, setRows] = useState<UserAdmin[] | null>(null);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(params.get("row") || null);
  const [draftQ, setDraftQ] = useState(q);
  const [roles, setRoles] = useState<RoleOut[]>([]);

  useListReturn("/admin/users", selectedId);
  useEffect(() => setDraftQ(q), [q]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (draftQ.trim() === q) return;
      const next = new URLSearchParams(params);
      if (!draftQ.trim()) next.delete("q");
      else next.set("q", draftQ.trim());
      next.delete("offset");
      setParams(next);
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [draftQ]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    void listRoles()
      .then(setRoles)
      .catch(() => setRoles([]));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    void listUsers({
      q: q || undefined,
      isActive: active === "1" ? true : active === "0" ? false : null,
      role: role || undefined,
      limit: PAGE,
      offset,
    })
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
  }, [q, active, role, offset]);

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
        cell: (row) => row.name,
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
        header: "Situação",
        visibility: "always",
        priority: 0,
        minWidth: "6rem",
        cell: (row) =>
          row.is_active ? (
            <span className="status-badge status-ok">Ativo</span>
          ) : (
            <span className="status-badge status-neutral">Inativo</span>
          ),
      },
      {
        id: "last_login",
        header: "Último acesso",
        visibility: "standard",
        priority: 1,
        minWidth: "9rem",
        cell: (row) => formatDateTime(row.last_login),
      },
    ],
    [],
  );

  if (!canRead(user)) {
    return <ErrorState message="Sem permissão para usuários." />;
  }
  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState message="Carregando usuários…" />;

  const hasQuery = Boolean(q || active || role);

  return (
    <section className="panel dense" data-testid="users-list-page">
      <PageHeader
        title="Usuários"
        subtitle="Acesso e papéis · IAM-light"
        actions={
          canWrite(user) ? (
            <Link className="ui-button" to="/admin/users/new" data-testid="users-new-cta">
              + Novo usuário
            </Link>
          ) : null
        }
      />
      <FilterBar
        primary={
          <div className="stack-row" style={{ flexWrap: "wrap", gap: "0.5rem", alignItems: "center" }}>
            <TextInput
              data-testid="users-search"
              value={draftQ}
              onChange={(e) => setDraftQ(e.target.value)}
              placeholder="Buscar por nome ou e-mail"
              aria-label="Buscar usuários"
            />
            <FilterChip pressed={active === "1"} onClick={() => setParam("active", active === "1" ? "" : "1")}>
              Ativos
            </FilterChip>
            <FilterChip pressed={active === "0"} onClick={() => setParam("active", active === "0" ? "" : "0")}>
              Inativos
            </FilterChip>
            {roles.map((r) => (
              <FilterChip
                key={r.name}
                pressed={role === r.name}
                onClick={() => setParam("role", role === r.name ? "" : r.name)}
              >
                {roleLabel(r.name)}
              </FilterChip>
            ))}
          </div>
        }
      />
      {rows.length === 0 ? (
        <EmptyState
          title={hasQuery ? "Nenhum resultado" : "Nenhum usuário"}
          message={hasQuery ? "Nenhum usuário corresponde à busca ou aos filtros." : "Crie o primeiro usuário."}
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
            onRowClick={(row) => {
              rememberRow(row.id);
              navigate(`/admin/users/${row.id}`, { state: { returnTo } });
            }}
          />
          <PaginationSummary offset={offset} limit={PAGE} total={total} loadedCount={rows.length} />
          {total > PAGE ? (
            <div className="page-btns">
              <button
                type="button"
                className="ui-button ui-button--secondary"
                disabled={offset === 0}
                onClick={() => {
                  const next = new URLSearchParams(params);
                  const off = Math.max(0, offset - PAGE);
                  if (off <= 0) next.delete("offset");
                  else next.set("offset", String(off));
                  setParams(next);
                }}
              >
                Anterior
              </button>
              <button
                type="button"
                className="ui-button ui-button--secondary"
                disabled={offset + PAGE >= total}
                onClick={() => {
                  const next = new URLSearchParams(params);
                  next.set("offset", String(offset + PAGE));
                  setParams(next);
                }}
              >
                Próxima
              </button>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
