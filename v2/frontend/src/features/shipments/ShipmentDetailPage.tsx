import { Link, useNavigate, useParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { User } from "../auth/types";
import { canWriteLogistics } from "./shipmentPermissions";
import {
  addItem,
  addPackage,
  addPackagesBatch,
  addReference,
  advanceShipment,
  annulShipment,
  deleteShipment,
  getDerivedTotals,
  getDivergences,
  getShipment,
  listShipmentAudit,
  listShipmentDocuments,
  orderItemCandidates,
  removeItem,
  removePackage,
  removeReference,
  setPackageContents,
  updateItem,
  updatePackage,
  updatePackagesBatch,
  updateShipment,
  uploadShipmentDocument,
  upsertDocumentSummary,
  type DerivedTotals,
  type DivergenceRow,
  type Shipment,
  type ShipmentCandidate,
} from "./shipmentsApi";
import { listLogisticsProviders, type LogisticsProvider } from "./providersApi";
import { SHIPMENT_MODAL_OPTIONS, providerDisplayName, providerTypeLabel } from "./shipmentLabels";
import {
  ShipmentLogisticsPanels,
  contentDraftsToBody,
  packageFormToBody,
  type ContentDraft,
  type PackageFormState,
  type SummaryFormState,
} from "./ShipmentLogisticsPanels";
import { buildReturnTo } from "../../navigation/returnState";
import {
  AuditDocumentsBlock,
  Button,
  ConfirmationModal,
  ContextBreadcrumb,
  DateInput,
  EmptyState,
  ErrorState,
  FormField,
  LoadingState,
  Notice,
  OperationalTable,
  PageHeader,
  SectionCard,
  SelectField,
  StatusBadge,
  SummaryGrid,
  TextInput,
  formatDateOnly,
  compactQuantityWire,
  formatQuantity,
  type AuditEntry,
} from "../../ui";

type Props = { user: User };

const REFERENCE_TYPES = [
  "PACKING_LIST",
  "DDT",
  "BL",
  "AWB",
  "BOOKING",
  "CONTAINER",
  "FORWARDER_REFERENCE",
  "OTHER",
].map((v) => ({ value: v, label: v }));

const ADVANCE_LABELS: Record<string, string> = {
  PLANNED: "Reservar (BOOKED)",
  BOOKED: "Registrar saída (em trânsito)",
  IN_TRANSIT: "Registrar chegada",
};

const NEXT_STATUS: Record<string, string> = {
  PLANNED: "BOOKED",
  BOOKED: "IN_TRANSIT",
  IN_TRANSIT: "ARRIVED",
};

function displayStatus(shipment: Shipment) {
  return shipment.cancelled_at ? "CANCELLED" : shipment.status;
}

function todayIsoDate() {
  return new Date().toISOString().slice(0, 10);
}

function divergenceFieldLabel(field: string): string {
  switch (field) {
    case "pallet_count":
      return "Paletes (documento vs volumes PALLET)";
    case "carton_count":
      return "Caixas";
    case "net_weight_kg":
      return "Peso líquido (kg)";
    case "gross_weight_kg":
      return "Peso bruto (kg)";
    case "volume_m3":
      return "Volume (m³)";
    default:
      return field;
  }
}

function palletDivergenceCopy(
  rows: DivergenceRow[],
  derived: DerivedTotals | null,
): string | null {
  const pallet = rows.flatMap((r) => r.diffs).find((d) => d.field === "pallet_count" && d.is_significant);
  if (!pallet) return null;
  const cartons = derived?.carton_count ?? 0;
  return (
    `O documento declara ${pallet.declared} palete(s), mas os volumes detalhados importados ` +
    `são ${cartons} caixa(s) e nenhum volume do tipo PALLET. Palete no cabeçalho do packing ` +
    `não é o mesmo que um volume PALLET. Isso não impede o embarque.`
  );
}

type OrderItemPickerProps = {
  open: boolean;
  busy: boolean;
  onClose: () => void;
  onAdd: (candidate: ShipmentCandidate, quantity: string) => void;
};

function OrderItemPicker({ open, busy, onClose, onAdd }: OrderItemPickerProps) {
  const [orderCode, setOrderCode] = useState("");
  const [sku, setSku] = useState("");
  const [candidates, setCandidates] = useState<ShipmentCandidate[]>([]);
  const [selected, setSelected] = useState<ShipmentCandidate | null>(null);
  const [qty, setQty] = useState("1");
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setOrderCode("");
      setSku("");
      setCandidates([]);
      setSelected(null);
      setQty("1");
      setSearchError(null);
    }
  }, [open]);

  async function search() {
    setSearchError(null);
    if (!orderCode.trim()) {
      setSearchError("Código do pedido é obrigatório");
      return;
    }
    try {
      const rows = await orderItemCandidates({
        order_code: orderCode.trim(),
        sku: sku.trim() || undefined,
      });
      setCandidates(rows);
      setSelected(rows[0] ?? null);
      if (rows.length === 0) setSearchError("Nenhum item elegível encontrado");
    } catch (e) {
      setSearchError(e instanceof Error ? e.message : "Erro na busca");
    }
  }

  return (
    <ConfirmationModal
      open={open}
      title="Adicionar item comercial"
      confirmLabel="Adicionar"
      busy={busy}
      onCancel={onClose}
      onConfirm={() => {
        if (!selected) return;
        onAdd(selected, qty.trim() || "1");
      }}
    >
      <div className="stack">
        <FormField label="Pedido (código)" htmlFor="picker-order-code" required>
          <TextInput
            id="picker-order-code"
            data-testid="picker-order-code"
            value={orderCode}
            onChange={(e) => setOrderCode(e.target.value)}
          />
        </FormField>
        <FormField label="SKU (opcional)" htmlFor="picker-sku">
          <TextInput
            id="picker-sku"
            data-testid="picker-sku"
            value={sku}
            onChange={(e) => setSku(e.target.value)}
          />
        </FormField>
        <Button type="button" variant="secondary" onClick={() => void search()}>
          Buscar candidatos
        </Button>
        {searchError ? (
          <Notice tone="danger" className="error">
            {searchError}
          </Notice>
        ) : null}
        {candidates.length > 0 ? (
          <>
            <FormField label="Item" htmlFor="picker-candidate">
              <SelectField
                id="picker-candidate"
                data-testid="picker-candidate"
                value={selected ? String(selected.order_item_id) : ""}
                onChange={(e) => {
                  const id = Number(e.target.value);
                  setSelected(candidates.find((c) => c.order_item_id === id) ?? null);
                }}
                options={candidates.map((c) => ({
                  value: String(c.order_item_id),
                  label: `${c.sku} · residual ${formatQuantity(c.residual_qty)}`,
                }))}
              />
            </FormField>
            <FormField label="Quantidade" htmlFor="picker-qty" required>
              <TextInput
                id="picker-qty"
                data-testid="picker-qty"
                value={qty}
                onChange={(e) => setQty(e.target.value)}
              />
            </FormField>
          </>
        ) : null}
      </div>
    </ConfirmationModal>
  );
}

export function ShipmentDetailPage({ user }: Props) {
  const navigate = useNavigate();
  const { shipmentId } = useParams();
  const id = Number(shipmentId);
  const shipmentsReturn = buildReturnTo("/shipments");

  const [shipment, setShipment] = useState<Shipment | null>(null);
  const [derived, setDerived] = useState<DerivedTotals | null>(null);
  const [divergences, setDivergences] = useState<DivergenceRow[]>([]);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [modal, setModal] = useState("");
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [providerId, setProviderId] = useState("");
  const [providers, setProviders] = useState<LogisticsProvider[]>([]);
  const [plannedDeparture, setPlannedDeparture] = useState("");
  const [plannedArrival, setPlannedArrival] = useState("");
  const [notes, setNotes] = useState("");

  const [draftQty, setDraftQty] = useState<Record<number, string>>({});
  const [refType, setRefType] = useState("BL");
  const [refValue, setRefValue] = useState("");
  const [documents, setDocuments] = useState<
    Array<{ id: number; original_filename: string; role?: string | null }>
  >([]);

  const [pickerOpen, setPickerOpen] = useState(false);
  const [advanceOpen, setAdvanceOpen] = useState(false);
  const [advanceDate, setAdvanceDate] = useState(todayIsoDate());
  const [annulOpen, setAnnulOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const [busyResumo, setBusyResumo] = useState(false);
  const [busyItems, setBusyItems] = useState(false);
  const [busyPackages, setBusyPackages] = useState(false);
  const [busyDocs, setBusyDocs] = useState(false);
  const [busyRefs, setBusyRefs] = useState(false);
  const [busyAdvance, setBusyAdvance] = useState(false);
  const [busyAnnul, setBusyAnnul] = useState(false);
  const [busyDelete, setBusyDelete] = useState(false);

  const write = canWriteLogistics(user);
  const cancelled = !!shipment?.cancelled_at;
  const status = shipment?.status ?? "";
  const structureEditable = write && status === "PLANNED" && !cancelled;
  const headerEditable = write && !cancelled && (status === "PLANNED" || status === "BOOKED");
  const notesEditable = write && !cancelled;
  const nextStatus = NEXT_STATUS[status];

  const syncForm = useCallback((data: Shipment) => {
    setModal(data.modal ?? "");
    setOrigin(data.origin ?? "");
    setDestination(data.destination ?? "");
    setProviderId(data.logistics_provider_id != null ? String(data.logistics_provider_id) : "");
    setPlannedDeparture(data.planned_departure ?? "");
    setPlannedArrival(data.planned_arrival ?? "");
    setNotes(data.notes ?? "");
  }, []);

  const reloadTotals = useCallback(async (shipmentId: number) => {
    const [d, div] = await Promise.all([
      getDerivedTotals(shipmentId),
      getDivergences(shipmentId),
    ]);
    setDerived(d);
    setDivergences(div);
  }, []);

  const reloadDocs = useCallback(async () => {
    try {
      setDocuments(await listShipmentDocuments(id));
    } catch {
      setDocuments([]);
    }
  }, [id]);

  const reloadAll = useCallback(async () => {
    const data = await getShipment(id);
    setShipment(data);
    syncForm(data);
    await reloadTotals(id);
    await reloadDocs();
    const events = await listShipmentAudit(id);
    setAudit(
      events.map((e) => ({
        id: e.id,
        action: e.action,
        at: e.created_at,
        actor: e.actor_id,
        detail: e.reason_code ?? e.details,
      })),
    );
  }, [id, reloadDocs, reloadTotals, syncForm]);

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    let cancelled = false;
    setLoading(true);
    void reloadAll()
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id, reloadAll]);

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
      } catch {
        /* form still usable with empty options */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!shipment || providerId || !headerEditable) return;
    if (providers.length === 1) {
      setProviderId(String(providers[0].id));
    }
  }, [shipment, providerId, providers, headerEditable]);

  async function handle409<T>(fn: () => Promise<T>, preserveDraft = false): Promise<T | null> {
    try {
      return await fn();
    } catch (e) {
      const st = (e as Error & { status?: number }).status;
      if (st === 409) {
        const fresh = await getShipment(id);
        setShipment(fresh);
        syncForm(fresh);
        if (!preserveDraft) setDraftQty({});
        setError(
          "Conflito de versão — estado recarregado. Revise e tente de novo (rascunhos locais preservados quando aplicável).",
        );
        return null;
      }
      throw e;
    }
  }

  const significantDivergence = useMemo(
    () => divergences.some((row) => row.is_significant),
    [divergences],
  );
  const palletCopy = useMemo(
    () => palletDivergenceCopy(divergences, derived),
    [divergences, derived],
  );
  const otherSignificantDivergence = useMemo(
    () =>
      divergences.some((row) =>
        row.diffs.some((d) => d.is_significant && d.field !== "pallet_count"),
      ),
    [divergences],
  );

  if (error && !shipment) return <ErrorState message={error} />;
  if (loading || !shipment) return <LoadingState message="Carregando embarque…" />;

  const current = shipment;

  const canAdvance = write && !cancelled && !!nextStatus;
  const canAnnul = write && status === "PLANNED" && !cancelled;
  const canDelete =
    write &&
    status === "PLANNED" &&
    !cancelled &&
    (current.items?.length ?? 0) === 0 &&
    (current.packages?.length ?? 0) === 0;

  async function saveResumo() {
    if (!headerEditable && !notesEditable) return;
    setBusyResumo(true);
    setError(null);
    try {
      const body =
        status === "PLANNED"
          ? {
              expected_version: current.version,
              modal: modal || null,
              origin: origin.trim() || null,
              destination: destination.trim() || null,
              logistics_provider_id: providerId ? Number(providerId) : null,
              planned_departure: plannedDeparture || null,
              planned_arrival: plannedArrival || null,
              notes: notes.trim() || null,
            }
          : status === "BOOKED"
            ? {
                expected_version: current.version,
                logistics_provider_id: providerId ? Number(providerId) : null,
                planned_departure: plannedDeparture || null,
                planned_arrival: plannedArrival || null,
                notes: notes.trim() || null,
              }
            : {
                expected_version: current.version,
                notes: notes.trim() || null,
              };
      const updated = await handle409(() => updateShipment(id, body));
      if (updated) {
        setShipment(updated);
        syncForm(updated);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyResumo(false);
    }
  }

  async function onAdvance() {
    if (!canAdvance) return;
    setBusyAdvance(true);
    setError(null);
    try {
      const updated = await handle409(() =>
        advanceShipment(id, {
          expected_version: current.version,
          event_date: advanceDate,
        }),
      );
      if (updated) {
        setShipment(updated);
        syncForm(updated);
        setAdvanceOpen(false);
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyAdvance(false);
    }
  }

  async function onAnnul() {
    setBusyAnnul(true);
    setError(null);
    try {
      const updated = await handle409(() => annulShipment(id, current.version));
      if (updated) {
        setShipment(updated);
        syncForm(updated);
        setAnnulOpen(false);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyAnnul(false);
    }
  }

  async function onDelete() {
    setBusyDelete(true);
    setError(null);
    try {
      await handle409(() => deleteShipment(id, current.version));
      navigate(shipmentsReturn);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyDelete(false);
    }
  }

  async function onAddItem(candidate: ShipmentCandidate, quantity: string) {
    setBusyItems(true);
    setError(null);
    try {
      const updated = await handle409(
        () =>
          addItem(id, {
            expected_version: current.version,
            order_item_id: candidate.order_item_id,
            quantity,
          }),
        true,
      );
      if (updated) {
        setShipment(updated);
        setPickerOpen(false);
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyItems(false);
    }
  }

  async function saveItemQty(itemId: number) {
    const quantity = draftQty[itemId];
    if (!quantity) return;
    setBusyItems(true);
    setError(null);
    try {
      const updated = await handle409(
        () =>
          updateItem(id, itemId, {
            expected_version: current.version,
            quantity,
          }),
        true,
      );
      if (updated) {
        setShipment(updated);
        setDraftQty((prev) => {
          const next = { ...prev };
          delete next[itemId];
          return next;
        });
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyItems(false);
    }
  }

  async function onRemoveItem(itemId: number) {
    setBusyItems(true);
    setError(null);
    try {
      const updated = await handle409(() => removeItem(id, itemId, current.version));
      if (updated) {
        setShipment(updated);
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyItems(false);
    }
  }

  async function onAddPackage(form: PackageFormState) {
    setBusyPackages(true);
    setError(null);
    try {
      const updated = await handle409(() =>
        addPackage(id, { expected_version: current.version, ...packageFormToBody(form) }),
      );
      if (updated) {
        setShipment(updated);
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyPackages(false);
    }
  }

  async function onUpdatePackage(packageId: number, form: PackageFormState) {
    setBusyPackages(true);
    setError(null);
    try {
      const updated = await handle409(() =>
        updatePackage(id, packageId, {
          expected_version: current.version,
          ...packageFormToBody(form),
        }),
      );
      if (updated) {
        setShipment(updated);
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyPackages(false);
    }
  }

  async function onBatchRange(form: PackageFormState, rangeFrom: string, rangeTo: string) {
    setBusyPackages(true);
    setError(null);
    try {
      const body = packageFormToBody(form);
      const updated = await handle409(() =>
        addPackagesBatch(id, {
          expected_version: current.version,
          range_from: Number(rangeFrom),
          range_to: Number(rangeTo),
          template: { ...body, package_count: 1 },
        }),
      );
      if (updated) {
        setShipment(updated);
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyPackages(false);
    }
  }

  async function onBatchHomogeneous(form: PackageFormState) {
    setBusyPackages(true);
    setError(null);
    try {
      const body = packageFormToBody(form);
      const updated = await handle409(() =>
        addPackagesBatch(id, {
          expected_version: current.version,
          packages: [body],
        }),
      );
      if (updated) {
        setShipment(updated);
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyPackages(false);
    }
  }

  async function onBatchUpdate(packageIds: number[], form: PackageFormState) {
    setBusyPackages(true);
    setError(null);
    try {
      const body = packageFormToBody(form);
      const updated = await handle409(() =>
        updatePackagesBatch(id, {
          expected_version: current.version,
          package_ids: packageIds,
          package_type: body.package_type,
          description: body.description,
          packaging_ncm: body.packaging_ncm,
          length: body.length,
          width: body.width,
          height: body.height,
          dimension_unit: body.dimension_unit,
          raw_dimensions: body.raw_dimensions,
          net_weight_kg: body.net_weight_kg,
          gross_weight_kg: body.gross_weight_kg,
          volume_m3: body.volume_m3,
          source_document_id: body.source_document_id,
        }),
      );
      if (updated) {
        setShipment(updated);
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyPackages(false);
    }
  }

  async function onSaveContents(packageId: number, drafts: ContentDraft[]) {
    setBusyPackages(true);
    setError(null);
    try {
      const updated = await handle409(() =>
        setPackageContents(id, packageId, {
          expected_version: current.version,
          contents: contentDraftsToBody(drafts),
        }),
      );
      if (updated) {
        setShipment(updated);
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyPackages(false);
    }
  }

  async function onSaveSummary(form: SummaryFormState) {
    if (!form.document_id) {
      setError("Selecione um documento para o resumo declarado");
      return;
    }
    setBusyPackages(true);
    setError(null);
    try {
      const empty = (v: string) => (v.trim() === "" ? null : v.trim());
      const updated = await handle409(() =>
        upsertDocumentSummary(id, {
          expected_version: current.version,
          document_id: Number(form.document_id),
          declared_net_weight_kg: empty(form.declared_net_weight_kg),
          declared_gross_weight_kg: empty(form.declared_gross_weight_kg),
          declared_pallet_count: form.declared_pallet_count
            ? Number(form.declared_pallet_count)
            : null,
          declared_carton_count: form.declared_carton_count
            ? Number(form.declared_carton_count)
            : null,
          declared_volume_m3: empty(form.declared_volume_m3),
          declared_provenance: empty(form.declared_provenance),
          raw_notes: empty(form.raw_notes),
        }),
      );
      if (updated) {
        setShipment(updated);
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyPackages(false);
    }
  }

  async function onUploadDoc(file: File) {
    setBusyDocs(true);
    setError(null);
    try {
      await uploadShipmentDocument(id, file);
      await reloadDocs();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyDocs(false);
    }
  }

  async function onRemovePackage(packageId: number) {
    setBusyPackages(true);
    setError(null);
    try {
      const updated = await handle409(() => removePackage(id, packageId, current.version));
      if (updated) {
        setShipment(updated);
        await reloadTotals(id);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyPackages(false);
    }
  }

  async function onAddReference() {
    if (!refValue.trim()) return;
    setBusyRefs(true);
    setError(null);
    try {
      const updated = await handle409(() =>
        addReference(id, {
          expected_version: current.version,
          reference_type: refType,
          reference_value: refValue.trim(),
        }),
      );
      if (updated) {
        setShipment(updated);
        setRefValue("");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyRefs(false);
    }
  }

  async function onRemoveReference(referenceId: number) {
    setBusyRefs(true);
    setError(null);
    try {
      const updated = await handle409(() => removeReference(id, referenceId, current.version));
      if (updated) setShipment(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro");
    } finally {
      setBusyRefs(false);
    }
  }

  return (
    <section className="panel dense page-detail detail-shell" data-testid="shipment-detail">
      <ContextBreadcrumb
        items={[
          { label: "Logística", to: shipmentsReturn },
          { label: "Embarques", to: shipmentsReturn },
          { label: shipment.code },
        ]}
      />
      <PageHeader
        title={`Embarque ${shipment.code}`}
        subtitle={[shipment.modal, shipment.origin, shipment.destination]
          .filter(Boolean)
          .join(" · ")}
        actions={
          <div className="stack-row page-header-actions">
            <Link className="ui-button ui-button--secondary" to={shipmentsReturn}>
              Voltar à fila
            </Link>
            {canAdvance ? (
              <Button
                data-testid="shipment-advance-cta"
                onClick={() => {
                  setAdvanceDate(todayIsoDate());
                  setAdvanceOpen(true);
                }}
              >
                {ADVANCE_LABELS[status] ?? "Avançar"}
              </Button>
            ) : null}
            {canAnnul ? (
              <Button
                variant="secondary"
                data-testid="shipment-annul-cta"
                onClick={() => setAnnulOpen(true)}
              >
                Anular
              </Button>
            ) : null}
            {canDelete ? (
              <Button
                variant="secondary"
                data-testid="shipment-delete-cta"
                onClick={() => setDeleteOpen(true)}
              >
                Excluir
              </Button>
            ) : null}
          </div>
        }
      />

      <div className="stack-row">
        <StatusBadge status={displayStatus(shipment)} entity="shipment" />
        <span className="muted">Revisão {shipment.version}</span>
      </div>

      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}

      {!structureEditable && !cancelled && status !== "PLANNED" ? (
        <Notice tone="info" data-testid="readonly-banner">
          Embarque somente leitura na estrutura — <StatusBadge status={status} entity="shipment" />
        </Notice>
      ) : null}

      {cancelled ? (
        <Notice tone="warning" data-testid="cancelled-banner">
          Embarque anulado em {formatDateOnly(shipment.cancelled_at)}
        </Notice>
      ) : null}

      {write && status === "PLANNED" && !cancelled && (!modal || !providerId) ? (
        <Notice tone="warning" data-testid="shipment-booked-prereq">
          Para reservar (BOOKED), informe modal e prestador no resumo e salve antes de avançar.
          O packing deixa o embarque planejado sem modal.
        </Notice>
      ) : null}

      <SectionCard title="Resumo">
        <div className="form-grid">
          <FormField label="Modal de transporte" htmlFor="detail-modal">
            <SelectField
              id="detail-modal"
              data-testid="detail-modal"
              value={modal}
              disabled={!structureEditable}
              onChange={(e) => setModal(e.target.value)}
              placeholder="Selecione o modal"
              options={[...SHIPMENT_MODAL_OPTIONS]}
            />
          </FormField>
          <FormField label="Origem" htmlFor="detail-origin">
            <TextInput
              id="detail-origin"
              value={origin}
              disabled={!structureEditable}
              onChange={(e) => setOrigin(e.target.value)}
            />
          </FormField>
          <FormField label="Destino" htmlFor="detail-destination">
            <TextInput
              id="detail-destination"
              value={destination}
              disabled={!structureEditable}
              onChange={(e) => setDestination(e.target.value)}
            />
          </FormField>
          <FormField
            label="Empresa transportadora"
            htmlFor="detail-provider"
            hint={
              shipment?.logistics_provider
                ? providerTypeLabel(shipment.logistics_provider.provider_type)
                : shipment?.carrier_name_snapshot && !providerId
                  ? `Legado: ${shipment.carrier_name_snapshot}`
                  : undefined
            }
          >
            <SelectField
              id="detail-provider"
              data-testid="detail-provider"
              value={providerId}
              disabled={!headerEditable}
              onChange={(e) => setProviderId(e.target.value)}
              placeholder="Selecione a transportadora"
              options={providers.map((p) => ({
                value: String(p.id),
                label: providerDisplayName(p),
              }))}
            />
          </FormField>
          <FormField label="Saída prevista" htmlFor="detail-planned-departure" hint="dd/mm/aaaa">
            <DateInput
              id="detail-planned-departure"
              value={plannedDeparture}
              disabled={!headerEditable}
              onChange={(e) => setPlannedDeparture(e.target.value)}
            />
          </FormField>
          <FormField label="Chegada prevista" htmlFor="detail-planned-arrival" hint="dd/mm/aaaa">
            <DateInput
              id="detail-planned-arrival"
              value={plannedArrival}
              disabled={!headerEditable}
              onChange={(e) => setPlannedArrival(e.target.value)}
            />
          </FormField>
          <FormField label="Notas" htmlFor="detail-notes" className="span-2">
            <TextInput
              id="detail-notes"
              value={notes}
              disabled={!notesEditable}
              onChange={(e) => setNotes(e.target.value)}
            />
          </FormField>
        </div>
        <SummaryGrid
          items={[
            { label: "Saída real", value: formatDateOnly(shipment.actual_departure) },
            { label: "Chegada real", value: formatDateOnly(shipment.actual_arrival) },
            { label: "Status desde", value: formatDateOnly(shipment.status_changed_at) },
          ]}
        />
        {headerEditable || notesEditable ? (
          <div className="actions">
            <Button busy={busyResumo} data-testid="shipment-save-resumo" onClick={() => void saveResumo()}>
              Salvar resumo
            </Button>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Itens comerciais" data-testid="shipment-items">
        {structureEditable ? (
          <div className="actions">
            <Button
              type="button"
              data-testid="shipment-add-item"
              onClick={() => setPickerOpen(true)}
            >
              Adicionar item
            </Button>
          </div>
        ) : null}
        {(shipment.items?.length ?? 0) === 0 ? (
          <EmptyState message="Nenhum item comercial" />
        ) : (
          <OperationalTable density="finance">
            <thead>
              <tr>
                <th>Pedido</th>
                <th>SKU</th>
                <th>Descrição</th>
                <th className="num">Qtd</th>
                <th className="num">Residual</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {shipment.items?.map((item) => {
                const qtyValue = draftQty[item.id] ?? compactQuantityWire(item.quantity);
                return (
                  <tr key={item.id}>
                    <td>{item.order_code ?? item.order_id}</td>
                    <td>{item.sku ?? "—"}</td>
                    <td>{item.description ?? "—"}</td>
                    <td className="num">
                      {structureEditable ? (
                        <TextInput
                          data-testid={`item-qty-${item.id}`}
                          className="num"
                          value={qtyValue}
                          onChange={(e) =>
                            setDraftQty((prev) => ({ ...prev, [item.id]: e.target.value }))
                          }
                        />
                      ) : (
                        formatQuantity(item.quantity)
                      )}
                    </td>
                    <td className="num">{formatQuantity(item.residual_qty ?? "—")}</td>
                    <td>
                      {structureEditable ? (
                        <div className="stack-row">
                          {draftQty[item.id] ? (
                            <Button
                              type="button"
                              variant="ghost"
                              busy={busyItems}
                              onClick={() => void saveItemQty(item.id)}
                            >
                              Salvar
                            </Button>
                          ) : null}
                          <Button
                            type="button"
                            variant="ghost"
                            busy={busyItems}
                            data-testid={`shipment-remove-item-${item.id}`}
                            onClick={() => void onRemoveItem(item.id)}
                          >
                            Remover
                          </Button>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </OperationalTable>
        )}
      </SectionCard>

      <ShipmentLogisticsPanels
        shipment={shipment}
        structureEditable={structureEditable}
        busy={busyPackages}
        documents={documents}
        uploadBusy={busyDocs}
        onUpload={(file) => void onUploadDoc(file)}
        onAddPackage={(form) => void onAddPackage(form)}
        onUpdatePackage={(packageId, form) => void onUpdatePackage(packageId, form)}
        onRemovePackage={(packageId) => void onRemovePackage(packageId)}
        onBatchRange={(form, from, to) => void onBatchRange(form, from, to)}
        onBatchHomogeneous={(form) => void onBatchHomogeneous(form)}
        onBatchUpdate={(ids, form) => void onBatchUpdate(ids, form)}
        onSaveContents={(packageId, drafts) => void onSaveContents(packageId, drafts)}
        onSaveSummary={(form) => void onSaveSummary(form)}
      />

      <SectionCard title="Referências">
        {structureEditable ? (
          <div className="line-row">
            <SelectField
              data-testid="reference-type"
              value={refType}
              onChange={(e) => setRefType(e.target.value)}
              options={REFERENCE_TYPES}
            />
            <TextInput
              data-testid="reference-value"
              placeholder="Valor"
              value={refValue}
              onChange={(e) => setRefValue(e.target.value)}
            />
            <Button type="button" busy={busyRefs} data-testid="shipment-add-reference" onClick={() => void onAddReference()}>
              Adicionar
            </Button>
          </div>
        ) : null}
        {(shipment.references?.length ?? 0) === 0 ? (
          <EmptyState message="Nenhuma referência" />
        ) : (
          <OperationalTable density="finance">
            <thead>
              <tr>
                <th>Tipo</th>
                <th>Valor</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {shipment.references?.map((ref) => (
                <tr key={ref.id}>
                  <td>{ref.reference_type}</td>
                  <td>{ref.reference_value}</td>
                  <td>
                    {structureEditable ? (
                      <Button
                        type="button"
                        variant="ghost"
                        busy={busyRefs}
                        onClick={() => void onRemoveReference(ref.id)}
                      >
                        Remover
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </OperationalTable>
        )}
      </SectionCard>

      <SectionCard title="Totais" data-testid="shipment-totals">
        {palletCopy ? (
          <Notice tone="warning" data-testid="divergence-pallet-notice">
            {palletCopy}
          </Notice>
        ) : null}
        {otherSignificantDivergence || (significantDivergence && !palletCopy) ? (
          <Notice tone="warning" data-testid="divergence-notice">
            Divergência significativa entre declarado e derivado — revise volumes e resumos documentais.
          </Notice>
        ) : null}
        {derived ? (
          <SummaryGrid
            items={[
              { label: "Peso líquido (kg)", value: String(derived.net_weight_kg) },
              { label: "Peso bruto (kg)", value: String(derived.gross_weight_kg) },
              { label: "Volume (m³)", value: String(derived.volume_m3) },
              { label: "Paletes", value: String(derived.pallet_count) },
              { label: "Caixas", value: String(derived.carton_count) },
              { label: "Linhas de volume", value: String(derived.package_row_count) },
            ]}
          />
        ) : (
          <LoadingState message="Carregando totais…" />
        )}
        {divergences.length > 0 ? (
          <OperationalTable density="finance">
            <thead>
              <tr>
                <th>Documento</th>
                <th>Campo</th>
                <th>Declarado</th>
                <th>Derivado</th>
                <th>Significativo</th>
              </tr>
            </thead>
            <tbody>
              {divergences.flatMap((row) =>
                row.diffs.map((diff, idx) => (
                  <tr key={`${row.document_id}-${diff.field}-${idx}`}>
                    <td>#{row.document_id}</td>
                    <td>{divergenceFieldLabel(diff.field)}</td>
                    <td>{String(diff.declared)}</td>
                    <td>{String(diff.derived)}</td>
                    <td>{diff.is_significant ? "Sim" : "—"}</td>
                  </tr>
                )),
              )}
            </tbody>
          </OperationalTable>
        ) : null}
      </SectionCard>

      <AuditDocumentsBlock
        documents={documents.map((d) => ({
          id: d.id,
          name: d.original_filename,
        }))}
        audit={audit}
        emptyDocuments="Nenhum documento anexado"
      />

      <OrderItemPicker
        open={pickerOpen}
        busy={busyItems}
        onClose={() => setPickerOpen(false)}
        onAdd={(candidate, quantity) => void onAddItem(candidate, quantity)}
      />

      <ConfirmationModal
        open={advanceOpen}
        title={ADVANCE_LABELS[status] ?? "Avançar status"}
        confirmLabel="Confirmar"
        busy={busyAdvance}
        onCancel={() => setAdvanceOpen(false)}
        onConfirm={() => void onAdvance()}
      >
        <p>
          Avançar para <StatusBadge status={nextStatus ?? ""} entity="shipment" /> — informe a data
          do evento.
        </p>
        <FormField label="Data do evento" htmlFor="advance-date" required>
          <DateInput
            id="advance-date"
            data-testid="advance-event-date"
            value={advanceDate}
            onChange={(e) => setAdvanceDate(e.target.value)}
          />
        </FormField>
      </ConfirmationModal>

      <ConfirmationModal
        open={annulOpen}
        title="Anular embarque"
        confirmLabel="Anular"
        busy={busyAnnul}
        onCancel={() => setAnnulOpen(false)}
        onConfirm={() => void onAnnul()}
      >
        <p>O embarque permanece no histórico como anulado e sai da fila padrão. Confirma?</p>
      </ConfirmationModal>

      <ConfirmationModal
        open={deleteOpen}
        title="Excluir embarque"
        confirmLabel="Excluir"
        busy={busyDelete}
        onCancel={() => setDeleteOpen(false)}
        onConfirm={() => void onDelete()}
      >
        <p>Exclusão definitiva — somente embarques PLANNED vazios. Confirma?</p>
      </ConfirmationModal>
    </section>
  );
}
