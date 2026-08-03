import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { User } from "../auth/types";
import { createImportProcess } from "./customsApi";
import { canWriteCustoms } from "./customsPermissions";
import {
  Button,
  ContextBreadcrumb,
  ErrorState,
  FormField,
  Notice,
  PageHeader,
  SectionCard,
  TextInput,
} from "../../ui";

type Props = { user: User };

export function CustomsCreatePage({ user }: Props) {
  const navigate = useNavigate();
  const [externalReference, setExternalReference] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!canWriteCustoms(user)) {
    return <ErrorState message="Sem permissão para criar processos aduaneiros." />;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const p = await createImportProcess({
        external_reference: externalReference.trim() || undefined,
        notes: notes.trim() || undefined,
      });
      navigate(`/customs/${p.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
      setBusy(false);
    }
  }

  return (
    <div data-testid="customs-create-page">
      <ContextBreadcrumb
        items={[
          { label: "Aduana" },
          { label: "Processos", to: "/customs" },
          { label: "Novo" },
        ]}
      />
      <PageHeader title="Novo processo aduaneiro" subtitle="Cria processo em rascunho." />
      {error ? <Notice tone="danger">{error}</Notice> : null}
      <SectionCard title="Identificação">
        <form onSubmit={(e) => void onSubmit(e)}>
          <FormField label="Referência externa (DUIMP)">
            <TextInput
              value={externalReference}
              onChange={(e) => setExternalReference(e.target.value)}
              data-testid="customs-external-ref"
              placeholder="Ex.: D00358/26"
            />
          </FormField>
          <FormField label="Notas">
            <TextInput
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              data-testid="customs-notes"
            />
          </FormField>
          <div className="form-actions">
            <Button type="submit" disabled={busy} data-testid="customs-create-submit">
              {busy ? "Salvando…" : "Criar"}
            </Button>
            <Link className="btn btn-ghost" to="/customs">
              Cancelar
            </Link>
          </div>
        </form>
      </SectionCard>
    </div>
  );
}
