import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { User } from "../auth/types";
import { createShipment } from "./shipmentsApi";
import { listLogisticsProviders, type LogisticsProvider } from "./providersApi";
import { canWriteLogistics } from "./shipmentPermissions";
import { SHIPMENT_MODAL_OPTIONS, providerDisplayName } from "./shipmentLabels";
import { buildReturnTo } from "../../navigation/returnState";
import {
  Button,
  ContextBreadcrumb,
  DateInput,
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

export function ShipmentCreatePage({ user }: Props) {
  const navigate = useNavigate();
  const shipmentsReturn = buildReturnTo("/shipments");
  const [modal, setModal] = useState("");
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [providerId, setProviderId] = useState("");
  const [plannedDeparture, setPlannedDeparture] = useState("");
  const [plannedArrival, setPlannedArrival] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [providers, setProviders] = useState<LogisticsProvider[] | null>(null);
  const [providersError, setProvidersError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const rows = await listLogisticsProviders({
          active_only: true,
          shipment_eligible_only: true,
          limit: 200,
        });
        if (cancelled) return;
        setProviders(rows);
        if (rows.length === 1) {
          setProviderId(String(rows[0].id));
        }
      } catch (e) {
        if (!cancelled) {
          setProvidersError(e instanceof Error ? e.message : "Erro ao carregar prestadores");
          setProviders([]);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const providerOptions = useMemo(
    () =>
      (providers ?? []).map((p) => ({
        value: String(p.id),
        label: providerDisplayName(p),
      })),
    [providers],
  );

  if (!canWriteLogistics(user)) {
    return <ErrorState message="Sem permissão para criar embarques." />;
  }

  if (providers === null) {
    return <LoadingState message="Carregando formulário…" />;
  }

  async function onCreate() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const shipment = await createShipment({
        modal: modal || null,
        origin: origin.trim() || null,
        destination: destination.trim() || null,
        logistics_provider_id: providerId ? Number(providerId) : null,
        planned_departure: plannedDeparture || null,
        planned_arrival: plannedArrival || null,
        notes: notes.trim() || null,
      });
      navigate(`/shipments/${shipment.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao criar embarque");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel dense page-form" data-testid="shipment-create-page">
      <ContextBreadcrumb
        items={[
          { label: "Logística", to: shipmentsReturn },
          { label: "Embarques", to: shipmentsReturn },
          { label: "Novo embarque" },
        ]}
      />
      <PageHeader
        title="Novo embarque"
        subtitle="Cadastre os dados básicos. Itens, volumes e documentos serão adicionados após a criação."
        actions={
          <Link className="ui-button ui-button--secondary" to={shipmentsReturn}>
            Voltar à fila
          </Link>
        }
      />
      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}
      {providersError ? (
        <Notice tone="danger" className="error">
          {providersError}
        </Notice>
      ) : null}

      <Notice tone="info">
        Modal e transportadora serão exigidos ao reservar (BOOKED).
      </Notice>

      <SectionCard title="Dados do embarque">
        {providers.length === 0 ? (
          <EmptyState
            title="Nenhum prestador cadastrado"
            message="Cadastre uma empresa transportadora antes de informar o prestador no embarque."
            action={
              <Link className="ui-button" to="/logistics-providers" data-testid="shipment-create-providers-cta">
                Cadastrar prestador
              </Link>
            }
          />
        ) : null}
        <div className="form-grid">
          <FormField label="Modal de transporte" htmlFor="shipment-modal">
            <SelectField
              id="shipment-modal"
              data-testid="shipment-modal"
              value={modal}
              onChange={(e) => setModal(e.target.value)}
              placeholder="Selecione o modal"
              options={[...SHIPMENT_MODAL_OPTIONS]}
            />
          </FormField>
          <FormField label="Origem" htmlFor="shipment-origin">
            <TextInput
              id="shipment-origin"
              data-testid="shipment-origin"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
            />
          </FormField>
          <FormField label="Destino" htmlFor="shipment-destination">
            <TextInput
              id="shipment-destination"
              data-testid="shipment-destination"
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
            />
          </FormField>
          <FormField label="Empresa transportadora" htmlFor="shipment-provider">
            <SelectField
              id="shipment-provider"
              data-testid="shipment-provider"
              value={providerId}
              onChange={(e) => setProviderId(e.target.value)}
              placeholder="Selecione a transportadora"
              options={providerOptions}
              disabled={providers.length === 0}
            />
          </FormField>
          <FormField
            label="Saída prevista"
            htmlFor="shipment-planned-departure"
            hint="dd/mm/aaaa"
          >
            <DateInput
              id="shipment-planned-departure"
              data-testid="shipment-planned-departure"
              value={plannedDeparture}
              onChange={(e) => setPlannedDeparture(e.target.value)}
            />
          </FormField>
          <FormField
            label="Chegada prevista"
            htmlFor="shipment-planned-arrival"
            hint="dd/mm/aaaa"
          >
            <DateInput
              id="shipment-planned-arrival"
              data-testid="shipment-planned-arrival"
              value={plannedArrival}
              onChange={(e) => setPlannedArrival(e.target.value)}
            />
          </FormField>
          <FormField label="Notas" htmlFor="shipment-notes" className="span-2">
            <TextInput
              id="shipment-notes"
              data-testid="shipment-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </FormField>
        </div>
      </SectionCard>

      <div className="actions">
        <Button type="button" busy={busy} data-testid="shipment-create-submit" onClick={() => void onCreate()}>
          Criar embarque
        </Button>
      </div>
    </section>
  );
}
