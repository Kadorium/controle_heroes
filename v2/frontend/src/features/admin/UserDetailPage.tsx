import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import { getUser, listRoles, patchUser, setUserPassword, type RoleOut, type UserAdmin } from "./identityApi";
import { listEntityAudit } from "../customs/customsApi";
import { buildReturnTo } from "../../navigation/returnState";
import {
  AuditDocumentsBlock,
  Button,
  ContextBreadcrumb,
  ErrorState,
  FormField,
  LoadingState,
  Notice,
  PageHeader,
  SectionCard,
  SelectField,
  TextInput,
  formatDateTime,
  roleLabel,
  type AuditEntry,
} from "../../ui";

type Props = { user: User };

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("users:write");
}

export function UserDetailPage({ user }: Props) {
  const { userId } = useParams();
  const location = useLocation();
  const listReturn =
    (location.state as { returnTo?: string } | null)?.returnTo || buildReturnTo("/admin/users");
  const id = Number(userId);
  const write = canWrite(user);
  const [row, setRow] = useState<UserAdmin | null>(null);
  const [roles, setRoles] = useState<RoleOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [name, setName] = useState("");
  const [roleId, setRoleId] = useState("");
  const [newPass, setNewPass] = useState("");
  const [newPass2, setNewPass2] = useState("");

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    let cancelled = false;
    void (async () => {
      try {
        const [u, rs] = await Promise.all([getUser(id), listRoles()]);
        if (cancelled) return;
        setRow(u);
        setName(u.name);
        setRoleId(String(u.role_id));
        setRoles(rs);
        const events = await listEntityAudit("user", String(id));
        if (!cancelled) {
          setAudit(
            events.map((e) => ({
              id: e.id,
              action: e.action,
              at: e.created_at,
              actor: e.actor_id,
            })),
          );
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (!Number.isFinite(id)) return <ErrorState message="Usuário inválido." />;
  if (error) return <ErrorState message={error} />;
  if (!row) return <LoadingState message="Carregando usuário…" />;

  async function save(extra?: { is_active?: boolean }) {
    if (busy || !row) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await patchUser(row.id, {
        name: name.trim(),
        role_id: Number(roleId),
        ...extra,
      });
      setRow(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setBusy(false);
    }
  }

  async function onSetPassword() {
    if (!row) return;
    if (newPass !== newPass2) {
      setError("As senhas não coincidem");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await setUserPassword(row.id, newPass);
      setNewPass("");
      setNewPass2("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao definir senha");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel dense" data-testid="user-detail-page">
      <ContextBreadcrumb items={[{ label: "Usuários", to: listReturn }, { label: row.name }]} />
      <PageHeader
        title={row.name}
        subtitle={`${roleLabel(row.role)} · ${row.is_active ? "Ativo" : "Inativo"}`}
        actions={
          <>
            <Link className="ui-button ui-button--secondary" to={listReturn}>
              Voltar à lista
            </Link>
            {write ? (
              <Button
                type="button"
                variant="secondary"
                busy={busy}
                data-testid="user-toggle-active"
                onClick={() => void save({ is_active: !row.is_active })}
              >
                {row.is_active ? "Inativar" : "Reativar"}
              </Button>
            ) : null}
          </>
        }
      />
      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}
      <SectionCard title="Perfil">
        <div className="form-grid">
          <FormField label="E-mail" htmlFor="ud-email">
            <TextInput id="ud-email" value={row.email} readOnly />
          </FormField>
          <FormField label="Nome" htmlFor="ud-name" required>
            <TextInput
              id="ud-name"
              data-testid="user-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!write}
            />
          </FormField>
          <FormField label="Papel" htmlFor="ud-role">
            <SelectField
              id="ud-role"
              data-testid="user-role"
              value={roleId}
              onChange={(e) => setRoleId(e.target.value)}
              disabled={!write}
              options={roles.map((r) => ({ value: String(r.id), label: roleLabel(r.name) }))}
            />
          </FormField>
          <FormField label="Último acesso" htmlFor="ud-last">
            <TextInput id="ud-last" value={row.last_login ? formatDateTime(row.last_login) : "—"} readOnly />
          </FormField>
        </div>
        <p className="muted">Permissões vêm do papel. Não há editor de permissões avulsas.</p>
        {write ? (
          <div className="actions">
            <Button type="button" busy={busy} data-testid="user-save" onClick={() => void save()}>
              Salvar
            </Button>
          </div>
        ) : null}
      </SectionCard>
      {write ? (
        <SectionCard title="Definir senha">
          <div className="form-grid">
            <FormField label="Nova senha" htmlFor="ud-pass">
              <TextInput
                id="ud-pass"
                data-testid="user-new-password"
                type="password"
                value={newPass}
                onChange={(e) => setNewPass(e.target.value)}
              />
            </FormField>
            <FormField label="Confirmar" htmlFor="ud-pass2">
              <TextInput
                id="ud-pass2"
                data-testid="user-new-password-confirm"
                type="password"
                value={newPass2}
                onChange={(e) => setNewPass2(e.target.value)}
              />
            </FormField>
          </div>
          <Button
            type="button"
            variant="secondary"
            busy={busy}
            data-testid="user-set-password"
            onClick={() => void onSetPassword()}
            disabled={!newPass}
          >
            Definir senha
          </Button>
        </SectionCard>
      ) : null}
      <AuditDocumentsBlock documents={[]} audit={audit} />
    </section>
  );
}
