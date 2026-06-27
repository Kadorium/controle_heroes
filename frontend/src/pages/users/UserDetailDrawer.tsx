import { useEffect, useMemo, useState } from "react";
import { Button } from "../../components";
import { usersApi, type AdminUser, type RoleOption } from "../../api";
import { canCancelUser, isUserActive, mergeRoleOptions, roleLabel } from "./userAdminUtils";

interface Props {
  open: boolean;
  user: AdminUser | null;
  currentUserId?: number;
  canWrite: boolean;
  onClose: () => void;
  onSaved: () => void;
  onDeleted: () => void;
}

export function UserDetailDrawer({
  open,
  user,
  currentUserId,
  canWrite,
  onClose,
  onSaved,
  onDeleted,
}: Props) {
  const isNew = !user?.id;
  const userActive = !user || isUserActive(user);
  const editingEnabled = canWrite && (isNew || userActive);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [roleName, setRoleName] = useState("operador");
  const [roles, setRoles] = useState<RoleOption[]>([]);
  const roleOptions = useMemo(
    () => mergeRoleOptions(roles, roleName),
    [roles, roleName],
  );
  const [resetPassword, setResetPassword] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [showCancel, setShowCancel] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!open) return;
    void usersApi.listRoles().then(setRoles).catch(() => setRoles([]));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    if (user) {
      setName(user.name);
      setEmail(user.email);
      setRoleName(user.role);
    } else {
      setName("");
      setEmail("");
      setRoleName("operador");
    }
    setPassword("");
    setResetPassword(false);
    setCancelReason("");
    setShowCancel(false);
    setError("");
  }, [open, user]);

  async function save() {
    if (!canWrite) return;
    setSaving(true);
    setError("");
    try {
      if (isNew) {
        if (password.length < 6) {
          setError("Senha deve ter no mínimo 6 caracteres");
          return;
        }
        await usersApi.create({
          email: email.trim(),
          name: name.trim(),
          password,
          role_name: roleName,
        });
      } else if (user) {
        const payload: { name?: string; role_name?: string; password?: string } = {
          name: name.trim(),
          role_name: roleName,
        };
        if (resetPassword && password.length >= 6) {
          payload.password = password;
        }
        await usersApi.update(user.id, payload);
      }
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setSaving(false);
    }
  }

  async function remove() {
    if (!user || cancelReason.trim().length < 3) {
      setError("Informe o motivo da anulação (mín. 3 caracteres)");
      return;
    }
    setDeleting(true);
    setError("");
    try {
      await usersApi.cancel(user.id, { reason: cancelReason.trim(), reason_code: "USER_CANCEL" });
      onDeleted();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao anular");
    } finally {
      setDeleting(false);
    }
  }

  if (!open) return null;

  return (
    <>
      <div className="drawer-back drawer-back--show" onClick={onClose} />
      <aside className="drawer drawer--wide drawer--show">
        <h3>{isNew ? "Novo usuário" : "Editar usuário"}</h3>
        {!isNew && user && !userActive && (
          <p className="meta">Este usuário está anulado. A edição está bloqueada até reativação manual no banco.</p>
        )}
        {!canWrite && (
          <p className="meta">Somente leitura — sua conta não tem permissão para alterar usuários.</p>
        )}
        {error && <p className="error">{error}</p>}

        <div className="form-stack">
          <label>
            Nome
            <input value={name} onChange={(e) => setName(e.target.value)} required disabled={!editingEnabled} />
          </label>
          <label>
            E-mail
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={!isNew || !editingEnabled}
              readOnly={!isNew}
            />
          </label>
          <label>
            Papel
            <select value={roleName} onChange={(e) => setRoleName(e.target.value)} disabled={!editingEnabled}>
              {roleOptions.map((r) => (
                <option key={r.name} value={r.name}>
                  {roleLabel(r.name)}
                </option>
              ))}
            </select>
          </label>
          {(isNew || resetPassword) && (
            <label>
              {isNew ? "Senha" : "Nova senha"}
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={6}
                disabled={!editingEnabled}
              />
            </label>
          )}
          {!isNew && editingEnabled && (
            <label className="checkbox-row">
              <input type="checkbox" checked={resetPassword} onChange={(e) => setResetPassword(e.target.checked)} />
              Redefinir senha
            </label>
          )}
        </div>

        {canWrite && editingEnabled && (
          <div className="drawer__actions">
            <Button type="button" variant="secondary" onClick={onClose}>
              Fechar
            </Button>
            <Button type="button" onClick={() => void save()} disabled={saving || !name.trim()}>
              Salvar
            </Button>
          </div>
        )}

        {!isNew && user && canWrite && userActive && canCancelUser(user, currentUserId) && (
          <section className="drawer__danger">
            {!showCancel ? (
              <Button type="button" variant="ghost" onClick={() => setShowCancel(true)}>
                Anular usuário
              </Button>
            ) : (
              <>
                <p className="drawer__sub">
                  A anulação revoga o acesso imediatamente, mas preserva o histórico de auditoria.
                </p>
                <label>
                  Motivo da anulação
                  <textarea
                    value={cancelReason}
                    onChange={(e) => setCancelReason(e.target.value)}
                    rows={3}
                    placeholder="Ex.: colaborador desligado"
                  />
                </label>
                <div className="drawer__actions">
                  <Button type="button" variant="secondary" onClick={() => setShowCancel(false)}>
                    Cancelar
                  </Button>
                  <Button
                    type="button"
                    variant="danger"
                    onClick={() => void remove()}
                    disabled={deleting || cancelReason.trim().length < 3}
                  >
                    Confirmar anulação
                  </Button>
                </div>
              </>
            )}
          </section>
        )}
      </aside>
    </>
  );
}
