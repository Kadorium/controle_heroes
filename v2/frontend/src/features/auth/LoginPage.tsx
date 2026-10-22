import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { postLoginPath } from "./safeNext";
import { Button, FormField, Notice, TextInput } from "../../ui";

type Props = {
  onSuccess: () => Promise<void> | void;
};

const DEV_LOGIN_APP_ENVS = new Set(["development", "test", "testing"]);
const DEV_EMAIL = "admin@epic.com.br";
const DEV_PASSWORD = "admin123";

function prefillFlag(): string | undefined {
  const flag = import.meta.env.VITE_LOGIN_PREFILL;
  return typeof flag === "string" ? flag : undefined;
}

function prefillFlagDisables(): boolean {
  const flag = prefillFlag();
  return flag === "0" || flag === "false";
}

function prefillFlagEnables(): boolean {
  const flag = prefillFlag();
  return flag === "1" || flag === "true";
}

/** Prefill só em Vite mode development ou quando VITE_LOGIN_PREFILL=1 (test). */
export function shouldPrefillLoginCredentials(): boolean {
  if (prefillFlagEnables()) return true;
  if (prefillFlagDisables()) return false;
  return import.meta.env.MODE === "development";
}

/** Atalho de ensaio: Vite dev/flag, ou APP_ENV development/test — nunca na faixa Operação. */
export function shouldOfferDevLoginShortcut(appEnv?: string | null, runtimeLane?: string | null): boolean {
  if (prefillFlagDisables()) return false;
  if (runtimeLane === "Operação") return false;
  if (shouldPrefillLoginCredentials()) return true;
  return DEV_LOGIN_APP_ENVS.has((appEnv || "").toLowerCase());
}

export function LoginPage({ onSuccess }: Props) {
  const prefill = shouldPrefillLoginCredentials();
  const [email, setEmail] = useState(prefill ? DEV_EMAIL : "");
  const [password, setPassword] = useState(prefill ? DEV_PASSWORD : "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showDevShortcut, setShowDevShortcut] = useState(shouldOfferDevLoginShortcut());
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const next = postLoginPath(params.get("next"));

  useEffect(() => {
    if (shouldOfferDevLoginShortcut()) return;
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/health", { credentials: "include" });
        if (!res.ok) return;
        const data = (await res.json()) as { app_env?: string; runtime_lane?: string };
        if (!cancelled && shouldOfferDevLoginShortcut(data.app_env, data.runtime_lane)) {
          setShowDevShortcut(true);
        }
      } catch {
        /* health opcional: sem atalho */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function finishLogin(res: Response) {
    if (!res.ok) {
      const body = await res.json().catch(() => null);
      throw new Error(body?.message || "Credenciais inválidas");
    }
    await onSuccess();
    navigate(next, { replace: true });
  }

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
      await finishLogin(res);
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

  async function onDevLogin() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/dev-login", {
        method: "POST",
        credentials: "include",
      });
      await finishLogin(res);
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
        {showDevShortcut ? (
          <>
            <Button
              type="button"
              variant="secondary"
              size="lg"
              busy={busy}
              data-testid="login-dev-shortcut"
              onClick={() => void onDevLogin()}
            >
              Acesso rápido (admin)
            </Button>
            <p className="login-dev-hint">Atalho de ensaio — some no ambiente de uso real.</p>
          </>
        ) : null}
      </form>
    </div>
  );
}
