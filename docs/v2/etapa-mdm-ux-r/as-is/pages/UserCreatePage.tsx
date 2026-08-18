import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { User } from "../auth/types";
import { createUser, listRoles, type RoleOut } from "./identityApi";
import { buildReturnTo } from "../../navigation/returnState";
import {
  Button,
  ContextBreadcrumb,
  ErrorState,
  FormField,
  Notice,
  PageHeader,
  SectionCard,
  SelectField,
  TextInput,
  roleLabel,
} from "../../ui";

type Props = { user: User };

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("users:write");
}

export function UserCreatePage({ user }: Props) {
  const nav = useNavigate();
  const listReturn = buildReturnTo("/admin/users");
  const [roles, setRoles] = useState<RoleOut[]>([]);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [roleId, setRoleId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void listRoles()
      .then((rows) => {
        setRoles(rows);
        const comprador = rows.find((r) => r.name === "comprador");
        if (comprador) setRoleId(String(comprador.id));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, []);

  if (!canWrite(user)) return <ErrorState message="Sem permissão para criar usuários." />;

  async function onSubmit() {
    if (busy) return;
    if (password !== password2) {
      setError("As senhas não coincidem");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await createUser({
        email: email.trim(),
        name: name.trim(),
        password,
        role_id: Number(roleId),
        is_active: true,
      });
      nav(`/admin/users/${created.id}`, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao criar usuário");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel dense" data-testid="user-create-page">
      <ContextBreadcrumb items={[{ label: "Usuários", to: listReturn }, { label: "Novo" }]} />
      <PageHeader
        title="Novo usuário"
        subtitle="A senha inicial é definida aqui. Não há convite por e-mail."
        actions={
          <Link className="ui-button ui-button--secondary" to={listReturn}>
            Voltar
          </Link>
        }
      />
      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}
      <SectionCard title="Dados">
        <div className="form-grid">
          <FormField label="Nome" htmlFor="u-name" required>
            <TextInput id="u-name" data-testid="user-name" value={name} onChange={(e) => setName(e.target.value)} />
          </FormField>
          <FormField label="E-mail" htmlFor="u-email" required>
            <TextInput
              id="u-email"
              data-testid="user-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </FormField>
          <FormField label="Papel" htmlFor="u-role" required>
            <SelectField
              id="u-role"
              data-testid="user-role"
              value={roleId}
              onChange={(e) => setRoleId(e.target.value)}
              options={roles.map((r) => ({ value: String(r.id), label: roleLabel(r.name) }))}
            />
          </FormField>
          <FormField label="Senha inicial" htmlFor="u-pass" required>
            <TextInput
              id="u-pass"
              data-testid="user-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </FormField>
          <FormField label="Confirmar senha" htmlFor="u-pass2" required>
            <TextInput
              id="u-pass2"
              data-testid="user-password-confirm"
              type="password"
              value={password2}
              onChange={(e) => setPassword2(e.target.value)}
            />
          </FormField>
        </div>
        <div className="actions">
          <Button
            type="button"
            busy={busy}
            data-testid="user-create-submit"
            onClick={() => void onSubmit()}
            disabled={!name.trim() || !email.trim() || !password || !roleId}
          >
            Criar
          </Button>
        </div>
      </SectionCard>
    </section>
  );
}
