import { FormEvent, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { sanitizeNextPath } from "./safeNext";
import { Button, FormField, Notice, TextInput } from "../../ui";

type Props = {
  onSuccess: () => Promise<void> | void;
};

/** Prefill só em Vite mode development ou quando VITE_LOGIN_PREFILL=1 (test). */
export function shouldPrefillLoginCredentials(): boolean {
  const mode = import.meta.env.MODE;
  const flag = import.meta.env.VITE_LOGIN_PREFILL;
  if (flag === "1" || flag === "true") return true;
  if (flag === "0" || flag === "false") return false;
  return mode === "development";
}

const DEV_EMAIL = "admin@epic.com.br";
const DEV_PASSWORD = "admin123";

export function LoginPage({ onSuccess }: Props) {
  const prefill = shouldPrefillLoginCredentials();
  const [email, setEmail] = useState(prefill ? DEV_EMAIL : "");
  const [password, setPassword] = useState(prefill ? DEV_PASSWORD : "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const next = sanitizeNextPath(params.get("next"));

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.message || "Credenciais inválidas");
      }
      await onSuccess();
      navigate(next, { replace: true });
    } catch (err) {
      if (err instanceof TypeError) {
        setError("Falha de rede. Verifique a conexão e tente novamente.");
      } else {
        setError(err instanceof Error ? err.message : "Erro");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page-center" data-testid="login-page">
      <form className="login-form" onSubmit={(e) => void onSubmit(e)} noValidate>
        <h1>Epic Controle</h1>
        <p>Acesse com suas credenciais corporativas.</p>
        <FormField label="E-mail" htmlFor="login-email">
          <TextInput
            id="login-email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            disabled={busy}
            required
          />
        </FormField>
        <FormField label="Senha" htmlFor="login-password">
          <TextInput
            id="login-password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            disabled={busy}
            required
          />
        </FormField>
        {error ? (
          <Notice tone="danger" className="error">
            {error}
          </Notice>
        ) : null}
        <Button type="submit" size="lg" busy={busy}>
          {busy ? "Entrando…" : "Entrar"}
        </Button>
      </form>
    </div>
  );
}
