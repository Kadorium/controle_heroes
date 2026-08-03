import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { User } from "../auth/types";
import {
  createLogisticsProvider,
  listLogisticsProviders,
  type LogisticsProvider,
} from "./providersApi";
import { canWriteLogistics } from "./shipmentPermissions";
import { PROVIDER_TYPE_OPTIONS, providerDisplayName, providerTypeLabel } from "./shipmentLabels";
import { buildReturnTo } from "../../navigation/returnState";
import {
  Button,
  ContextBreadcrumb,
  EmptyState,
  ErrorState,
  FormField,
  LoadingState,
  Notice,
  PageHeader,
  SectionCard,
  SelectField,
  TextInput,
} from "../../ui";

type Props = { user: User };

export function LogisticsProvidersPage({ user }: Props) {
  const shipmentsReturn = buildReturnTo("/shipments");
  const canWrite = canWriteLogistics(user);
  const [rows, setRows] = useState<LogisticsProvider[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [legalName, setLegalName] = useState("");
  const [tradeName, setTradeName] = useState("");
  const [providerType, setProviderType] = useState("TRANSPORTADOR");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function reload() {
    const data = await listLogisticsProviders({ limit: 200 });
    setRows(data);
  }

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const data = await listLogisticsProviders({ limit: 200 });
        if (!cancelled) setRows(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function onCreate() {
    if (!canWrite || busy) return;
    setBusy(true);
    setFormError(null);
    try {
      await createLogisticsProvider({
        legal_name: legalName.trim(),
        trade_name: tradeName.trim() || null,
        provider_type: providerType,
        active: true,
      });
      setLegalName("");
      setTradeName("");
      setProviderType("TRANSPORTADOR");
      await reload();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : "Erro ao cadastrar");
    } finally {
      setBusy(false);
    }
  }

  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState message="Carregando prestadores…" />;

  return (
    <section className="panel dense" data-testid="logistics-providers-page">
      <ContextBreadcrumb
        items={[
          { label: "Logística", to: shipmentsReturn },
          { label: "Prestadores" },
        ]}
      />
      <PageHeader
        title="Prestadores logísticos"
        subtitle="Cadastro de transportadoras, armadores, agentes e operadores."
        actions={
          <Link className="ui-button ui-button--secondary" to={shipmentsReturn}>
            Voltar aos embarques
          </Link>
        }
      />

      {canWrite ? (
        <SectionCard title="Novo prestador">
          {formError ? (
            <Notice tone="danger" className="error">
              {formError}
            </Notice>
          ) : null}
          <div className="form-grid">
            <FormField label="Razão social" htmlFor="provider-legal" required>
              <TextInput
                id="provider-legal"
                data-testid="provider-legal-name"
                value={legalName}
                onChange={(e) => setLegalName(e.target.value)}
              />
            </FormField>
            <FormField label="Nome fantasia" htmlFor="provider-trade">
              <TextInput
                id="provider-trade"
                data-testid="provider-trade-name"
                value={tradeName}
                onChange={(e) => setTradeName(e.target.value)}
              />
            </FormField>
            <FormField label="Tipo" htmlFor="provider-type" required>
              <SelectField
                id="provider-type"
                data-testid="provider-type"
                value={providerType}
                onChange={(e) => setProviderType(e.target.value)}
                options={[...PROVIDER_TYPE_OPTIONS]}
              />
            </FormField>
          </div>
          <div className="actions">
            <Button
              type="button"
              busy={busy}
              data-testid="provider-create-submit"
              onClick={() => void onCreate()}
              disabled={!legalName.trim()}
            >
              Cadastrar
            </Button>
          </div>
        </SectionCard>
      ) : null}

      {rows.length === 0 ? (
        <EmptyState
          title="Nenhum prestador"
          message="Cadastre o primeiro prestador para usá-lo nos embarques."
        />
      ) : (
        <SectionCard title="Cadastrados">
          <table className="data-table" data-testid="providers-table">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Tipo</th>
                <th>Ativo</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.id}>
                  <td>{providerDisplayName(p)}</td>
                  <td>{providerTypeLabel(p.provider_type)}</td>
                  <td>{p.active ? "Sim" : "Não"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </SectionCard>
      )}
    </section>
  );
}
