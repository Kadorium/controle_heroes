import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import { getSupplier, patchSupplier, type Supplier } from "./catalogApi";
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
  TextInput,
  type AuditEntry,
} from "../../ui";

type Props = { user: User };

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("catalog:write");
}

export function SupplierDetailPage({ user }: Props) {
  const { supplierId } = useParams();
  const location = useLocation();
  const listReturn =
    (location.state as { returnTo?: string } | null)?.returnTo || buildReturnTo("/catalog/suppliers");
  const id = Number(supplierId);
  const write = canWrite(user);
  const [row, setRow] = useState<Supplier | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [country, setCountry] = useState("");
  const [taxId, setTaxId] = useState("");

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    let cancelled = false;
    void (async () => {
      try {
        const s = await getSupplier(id);
        if (cancelled) return;
        setRow(s);
        setName(s.name);
        setCode(s.code ?? "");
        setCountry(s.country_code ?? "");
        setTaxId(s.tax_id ?? "");
        const events = await listEntityAudit("supplier", String(id));
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

  if (!Number.isFinite(id)) return <ErrorState message="Fornecedor inválido." />;
  if (error) return <ErrorState message={error} />;
  if (!row) return <LoadingState message="Carregando fornecedor…" />;

  async function save(extra?: { is_active?: boolean }) {
    if (busy || !row) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await patchSupplier(row.id, {
        name: name.trim(),
        code: code.trim() || null,
        country_code: country.trim() || null,
        tax_id: taxId.trim() || null,
        ...extra,
      });
      setRow(updated);
      setName(updated.name);
      setCode(updated.code ?? "");
      setCountry(updated.country_code ?? "");
      setTaxId(updated.tax_id ?? "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel dense" data-testid="supplier-detail-page">
      <ContextBreadcrumb items={[{ label: "Fornecedores", to: listReturn }, { label: row.name }]} />
      <PageHeader
        title={row.name}
        subtitle={row.is_active ? "Ativo" : "Inativo"}
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
                data-testid="supplier-toggle-active"
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
      <SectionCard title="Identidade">
        <div className="form-grid">
          <FormField label="Nome" htmlFor="s-name" required className="span-2">
            <TextInput
              id="s-name"
              data-testid="supplier-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={!write}
            />
          </FormField>
          <FormField label="Código" htmlFor="s-code">
            <TextInput
              id="s-code"
              data-testid="supplier-code"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={!write}
            />
          </FormField>
        </div>
      </SectionCard>
      <SectionCard title="Dados fiscais">
        <div className="form-grid">
          <FormField label="País (ISO-2)" htmlFor="s-country">
            <TextInput
              id="s-country"
              data-testid="supplier-country"
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              disabled={!write}
            />
          </FormField>
          <FormField label="Identificador fiscal" htmlFor="s-tax">
            <TextInput
              id="s-tax"
              data-testid="supplier-tax-id"
              value={taxId}
              onChange={(e) => setTaxId(e.target.value)}
              disabled={!write}
            />
          </FormField>
        </div>
      </SectionCard>
      {write ? (
        <div className="actions">
          <Button type="button" busy={busy} data-testid="supplier-save" onClick={() => void save()}>
            Salvar
          </Button>
        </div>
      ) : null}
      <AuditDocumentsBlock documents={[]} audit={audit} />
    </section>
  );
}
