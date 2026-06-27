import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { Card, EmptyState, LoadingState, PageHeader, Table, Button, useToast } from "../../components";
import { useAuth } from "../../context/AuthContext";
import { usersApi, type AdminUser } from "../../api";
import { hasPermission, PERM_USERS_READ, PERM_USERS_WRITE } from "../../utils/permissions";
import { UserDetailDrawer } from "./UserDetailDrawer";
import { roleLabel, statusLabel, type UserVisibility } from "./userAdminUtils";

const VISIBILITY: { id: UserVisibility; label: string }[] = [
  { id: "active", label: "Ativos" },
  { id: "cancelled", label: "Anulados" },
];

export function UsersPage() {
  const { user: currentUser } = useAuth();
  const toast = useToast();
  const [rows, setRows] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [visibility, setVisibility] = useState<UserVisibility>("active");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selected, setSelected] = useState<AdminUser | null>(null);

  const canRead = hasPermission(currentUser, PERM_USERS_READ);
  const canWrite = hasPermission(currentUser, PERM_USERS_WRITE);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setRows(await usersApi.list(visibility));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao carregar usuários");
    } finally {
      setLoading(false);
    }
  }, [visibility]);

  useEffect(() => {
    if (canRead) void load();
  }, [canRead, load]);

  if (!canRead) {
    return <Navigate to="/cadastros" replace />;
  }

  function openDrawer(user: AdminUser | null) {
    setSelected(user);
    setDrawerOpen(true);
  }

  return (
    <Card>
      <PageHeader
        title="Usuários"
        subtitle="Contas de acesso ao sistema"
        actions={
          canWrite ? (
            <Button onClick={() => openDrawer(null)}>Novo usuário</Button>
          ) : undefined
        }
      />
      {error && <p className="error">{error}</p>}

      <div className="order-queue__filters">
        {VISIBILITY.map((v) => (
          <button
            key={v.id}
            type="button"
            className={`chip-btn${visibility === v.id ? " chip-btn--active" : ""}`}
            onClick={() => setVisibility(v.id)}
          >
            {v.label}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingState />
      ) : rows.length === 0 ? (
        <EmptyState
          title="Nenhum usuário encontrado"
          description={
            visibility === "cancelled"
              ? "Não há usuários anulados no momento."
              : "Não há usuários ativos no momento."
          }
        />
      ) : (
        <>
          <p className="meta">
            {rows.length} usuário(s) · filtro: {visibility === "active" ? "Ativos" : "Anulados"}
          </p>
          <p className="meta">Clique em um usuário para editar ou anular.</p>
          <Table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>E-mail</th>
                <th>Papel</th>
                <th>Último login</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((u) => (
                <tr
                  key={u.id}
                  className="table-row--clickable"
                  onClick={() => openDrawer(u)}
                  title="Clique para editar"
                >
                  <td>{u.name}</td>
                  <td>{u.email}</td>
                  <td>{roleLabel(u.role)}</td>
                  <td>{u.last_login ? new Date(u.last_login).toLocaleString("pt-BR") : "—"}</td>
                  <td>{statusLabel(u)}</td>
                </tr>
              ))}
            </tbody>
          </Table>
        </>
      )}

      <UserDetailDrawer
        open={drawerOpen}
        user={selected}
        currentUserId={currentUser?.id}
        canWrite={canWrite}
        onClose={() => setDrawerOpen(false)}
        onSaved={() => {
          toast.success(selected ? "Usuário atualizado" : "Usuário criado");
          void load();
        }}
        onDeleted={() => {
          toast.success("Usuário anulado");
          void load();
        }}
      />
    </Card>
  );
}
