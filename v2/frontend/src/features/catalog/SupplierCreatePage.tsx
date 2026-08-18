import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { User } from "../auth/types";
import { createSupplier } from "./catalogApi";
import { buildReturnTo } from "../../navigation/returnState";
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

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("catalog:write");
}

export function SupplierCreatePage({ user }: Props) {
  const nav = useNavigate();
  const listReturn = buildReturnTo("/catalog/suppliers");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [country, setCountry] = useState("");
  const [taxId, setTaxId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (!canWrite(user)) return <ErrorState message="Sem permissão para criar fornecedores." />;

  async function onSubmit() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const s = await createSupplier({
        name: name.trim(),
        code: code.trim() || undefined,
        country_code: country.trim() || undefined,
        tax_id: taxId.trim() || undefined,
      });
      nav(`/catalog/suppliers/${s.id}`, { replace: true });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao criar fornecedor");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel dense" data-testid="supplier-create-page">
      <ContextBreadcrumb items={[{ label: "Fornecedores", to: listReturn }, { label: "Novo" }]} />
      <PageHeader
        title="Novo fornecedor"
        subtitle="O nome basta para começar."
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
      <SectionCard title="Identidade">
        <div className="form-grid">
          <FormField label="Nome" htmlFor="sup-name" required className="span-2">
            <TextInput
              id="sup-name"
              data-testid="supplier-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </FormField>
          <FormField label="Código" htmlFor="sup-code">
            <TextInput id="sup-code" data-testid="supplier-code" value={code} onChange={(e) => setCode(e.target.value)} />
          </FormField>
          <FormField label="País (ISO-2)" htmlFor="sup-country">
            <TextInput
              id="sup-country"
              data-testid="supplier-country"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
            />
          </FormField>
          <FormField label="Identificador fiscal" htmlFor="sup-tax" hint="P.IVA / VAT; só dígitos">
            <TextInput
              id="sup-tax"
              data-testid="supplier-tax-id"
              value={taxId}
              onChange={(e) => setTaxId(e.target.value)}
            />
          </FormField>
        </div>
        <div className="actions">
          <Button
            type="button"
            busy={busy}
            data-testid="supplier-create-submit"
            onClick={() => void onSubmit()}
            disabled={!name.trim()}
          >
            Criar
          </Button>
        </div>
      </SectionCard>
    </section>
  );
}
