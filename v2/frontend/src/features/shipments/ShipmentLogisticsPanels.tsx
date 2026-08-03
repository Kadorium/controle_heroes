import { useEffect, useMemo, useState } from "react";
import type { Shipment } from "./shipmentsApi";
import {
  Button,
  DocumentActions,
  EmptyState,
  FileUpload,
  FormField,
  Notice,
  OperationalTable,
  SectionCard,
  SelectField,
  SummaryGrid,
  TextInput,
  compactQuantityWire,
  formatQuantity,
} from "../../ui";

const PACKAGE_TYPES = [
  { value: "PALLET", label: "Palete" },
  { value: "CARTON", label: "Caixa" },
  { value: "BOX", label: "Box" },
  { value: "OTHER", label: "Outro" },
];

const DIMENSION_UNITS = [
  { value: "CM", label: "CM" },
  { value: "MM", label: "MM" },
  { value: "M", label: "M" },
];

const PROVENANCE_OPTIONS = [
  { value: "PACKING_LIST", label: "Packing List" },
  { value: "FATTURA_DOGANALE", label: "Fattura doganale (totais declarados — referência)" },
  { value: "MANUAL", label: "Manual" },
  { value: "OTHER", label: "Outro" },
];

const PROVENANCE_LABEL: Record<string, string> = Object.fromEntries(
  PROVENANCE_OPTIONS.map((o) => [o.value, o.label]),
);

export type PackageFormState = {
  package_type: string;
  package_count: string;
  external_package_no: string;
  description: string;
  packaging_ncm: string;
  length: string;
  width: string;
  height: string;
  dimension_unit: string;
  raw_dimensions: string;
  net_weight_kg: string;
  gross_weight_kg: string;
  volume_m3: string;
  parent_package_id: string;
  source_document_id: string;
};

export type ContentDraft = {
  shipment_item_id: string;
  contained_quantity: string;
  source_unit: string;
  source_line_reference: string;
  source_ncm: string;
  source_description: string;
  units_per_package: string;
  unit_net_weight_kg: string;
  unit_gross_weight_kg: string;
  source_total_net_weight_kg: string;
  source_total_gross_weight_kg: string;
};

export type SummaryFormState = {
  document_id: string;
  declared_net_weight_kg: string;
  declared_gross_weight_kg: string;
  declared_pallet_count: string;
  declared_carton_count: string;
  declared_volume_m3: string;
  declared_provenance: string;
  raw_notes: string;
};

export type ShipmentDoc = {
  id: number;
  original_filename: string;
  mime_type?: string | null;
  role?: string | null;
};

const emptyPackageForm = (): PackageFormState => ({
  package_type: "CARTON",
  package_count: "1",
  external_package_no: "",
  description: "",
  packaging_ncm: "",
  length: "",
  width: "",
  height: "",
  dimension_unit: "CM",
  raw_dimensions: "",
  net_weight_kg: "",
  gross_weight_kg: "",
  volume_m3: "",
  parent_package_id: "",
  source_document_id: "",
});

const emptyContent = (): ContentDraft => ({
  shipment_item_id: "",
  contained_quantity: "",
  source_unit: "PZ",
  source_line_reference: "",
  source_ncm: "",
  source_description: "",
  units_per_package: "",
  unit_net_weight_kg: "",
  unit_gross_weight_kg: "",
  source_total_net_weight_kg: "",
  source_total_gross_weight_kg: "",
});

type Props = {
  shipment: Shipment;
  structureEditable: boolean;
  busy: boolean;
  documents: ShipmentDoc[];
  uploadBusy: boolean;
  onUpload: (file: File) => void;
  onAddPackage: (form: PackageFormState) => void;
  onUpdatePackage: (packageId: number, form: PackageFormState) => void;
  onRemovePackage: (packageId: number) => void;
  onBatchRange: (form: PackageFormState, rangeFrom: string, rangeTo: string) => void;
  onBatchHomogeneous: (form: PackageFormState) => void;
  onBatchUpdate: (packageIds: number[], form: PackageFormState) => void;
  onSaveContents: (packageId: number, contents: ContentDraft[]) => void;
  onSaveSummary: (form: SummaryFormState) => void;
};

export function ShipmentLogisticsPanels({
  shipment,
  structureEditable,
  busy,
  documents,
  uploadBusy,
  onUpload,
  onAddPackage,
  onUpdatePackage,
  onRemovePackage,
  onBatchRange,
  onBatchHomogeneous,
  onBatchUpdate,
  onSaveContents,
  onSaveSummary,
}: Props) {
  const [form, setForm] = useState<PackageFormState>(emptyPackageForm);
  const [editId, setEditId] = useState<number | null>(null);
  const [rangeFrom, setRangeFrom] = useState("1");
  const [rangeTo, setRangeTo] = useState("10");
  const [selected, setSelected] = useState<number[]>([]);
  const [contentsPkgId, setContentsPkgId] = useState<number | null>(null);
  const [contents, setContents] = useState<ContentDraft[]>([emptyContent()]);
  const [summary, setSummary] = useState<SummaryFormState>({
    document_id: "",
    declared_net_weight_kg: "",
    declared_gross_weight_kg: "",
    declared_pallet_count: "",
    declared_carton_count: "",
    declared_volume_m3: "",
    declared_provenance: "PACKING_LIST",
    raw_notes: "",
  });

  const itemOptions = useMemo(
    () =>
      (shipment.items ?? []).map((i) => ({
        value: String(i.id),
        label: `#${i.id} · ${i.sku ?? "?"} · ${formatQuantity(i.quantity)}`,
      })),
    [shipment.items],
  );

  const docOptions = useMemo(
    () => documents.map((d) => ({ value: String(d.id), label: `#${d.id} · ${d.original_filename}` })),
    [documents],
  );

  const sticky = useMemo(() => {
    const pkgs = shipment.packages ?? [];
    const qty = pkgs.reduce((a, p) => a + (p.package_count ?? 0), 0);
    return {
      rows: pkgs.length,
      qty,
      net: pkgs.reduce((a, p) => a + Number(p.net_weight_kg ?? 0) * (p.package_count ?? 1), 0),
      gross: pkgs.reduce((a, p) => a + Number(p.gross_weight_kg ?? 0) * (p.package_count ?? 1), 0),
    };
  }, [shipment.packages]);

  function setField<K extends keyof PackageFormState>(key: K, value: PackageFormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function loadPackage(pkg: NonNullable<Shipment["packages"]>[number]) {
    setEditId(pkg.id);
    setForm({
      package_type: pkg.package_type,
      package_count: String(pkg.package_count),
      external_package_no: pkg.external_package_no ?? "",
      description: pkg.description ?? "",
      packaging_ncm: pkg.packaging_ncm ?? "",
      length: pkg.length ?? "",
      width: pkg.width ?? "",
      height: pkg.height ?? "",
      dimension_unit: pkg.dimension_unit ?? "CM",
      raw_dimensions: pkg.raw_dimensions ?? "",
      net_weight_kg: pkg.net_weight_kg ?? "",
      gross_weight_kg: pkg.gross_weight_kg ?? "",
      volume_m3: pkg.volume_m3 ?? "",
      parent_package_id: pkg.parent_package_id != null ? String(pkg.parent_package_id) : "",
      source_document_id: pkg.source_document_id != null ? String(pkg.source_document_id) : "",
    });
  }

  function openContents(pkg: NonNullable<Shipment["packages"]>[number]) {
    setContentsPkgId(pkg.id);
    if (pkg.contents?.length) {
      setContents(
        pkg.contents.map((c) => ({
          shipment_item_id: String(c.shipment_item_id),
          contained_quantity: compactQuantityWire(c.contained_quantity),
          source_unit: c.source_unit ?? "PZ",
          source_line_reference: c.source_line_reference ?? "",
          source_ncm: c.source_ncm ?? "",
          source_description: c.source_description ?? "",
          units_per_package: compactQuantityWire(c.units_per_package),
          unit_net_weight_kg: compactQuantityWire(c.unit_net_weight_kg),
          unit_gross_weight_kg: compactQuantityWire(c.unit_gross_weight_kg),
          source_total_net_weight_kg: compactQuantityWire(c.source_total_net_weight_kg),
          source_total_gross_weight_kg: compactQuantityWire(c.source_total_gross_weight_kg),
        })),
      );
    } else {
      setContents([emptyContent()]);
    }
  }

  useEffect(() => {
    if (contentsPkgId == null) return;
    document.getElementById("package-contents-heading")?.focus();
  }, [contentsPkgId]);

  function toggleSelect(id: number) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  return (
    <>
      <SectionCard title="Volumes" data-testid="shipment-packages">
        <Notice tone="info">
          Pesos e medidas do volume são físicos (por unidade × quantidade de volumes). Os dados da linha
          do Packing List (NCM do produto, unidades por volume, pesos unitários e totais de linha) ficam
          no conteúdo do volume — distintos do NCM da embalagem.
        </Notice>
        <SummaryGrid
          items={[
            { label: "Linhas", value: String(sticky.rows) },
            { label: "Σ volumes", value: String(sticky.qty) },
            { label: "Σ líquido físico", value: sticky.net.toFixed(2) },
            { label: "Σ bruto físico", value: sticky.gross.toFixed(2) },
          ]}
        />

        {structureEditable ? (
          <div className="stack" data-testid="package-editor">
            <h3 className="section-subtitle">Identificação</h3>
            <div className="form-grid">
              <FormField label="Tipo de volume" htmlFor="package-type">
                <SelectField
                  id="package-type"
                  data-testid="package-type"
                  value={form.package_type}
                  onChange={(e) => setField("package_type", e.target.value)}
                  options={PACKAGE_TYPES}
                />
              </FormField>
              <FormField label="Quantidade de volumes" htmlFor="package-count" hint="Ex.: N° Cartons">
                <TextInput
                  id="package-count"
                  data-testid="package-count"
                  value={form.package_count}
                  onChange={(e) => setField("package_count", e.target.value)}
                />
              </FormField>
              <FormField label="Número externo / CTNS" htmlFor="package-external-no">
                <TextInput
                  id="package-external-no"
                  data-testid="package-external-no"
                  value={form.external_package_no}
                  onChange={(e) => setField("external_package_no", e.target.value)}
                />
              </FormField>
              <FormField label="Volume pai (ID)" htmlFor="package-parent-id">
                <TextInput
                  id="package-parent-id"
                  data-testid="package-parent-id"
                  value={form.parent_package_id}
                  onChange={(e) => setField("parent_package_id", e.target.value)}
                />
              </FormField>
              <FormField label="Descrição" htmlFor="package-description" className="span-2">
                <TextInput
                  id="package-description"
                  data-testid="package-description"
                  value={form.description}
                  onChange={(e) => setField("description", e.target.value)}
                />
              </FormField>
            </div>

            <h3 className="section-subtitle">Embalagem</h3>
            <div className="form-grid">
              <FormField label="NCM da embalagem" htmlFor="package-packaging-ncm" hint="Ex.: 4819…">
                <TextInput
                  id="package-packaging-ncm"
                  data-testid="package-packaging-ncm"
                  value={form.packaging_ncm}
                  onChange={(e) => setField("packaging_ncm", e.target.value)}
                />
              </FormField>
              <FormField label="Medidas brutas (texto)" htmlFor="package-raw-dimensions">
                <TextInput
                  id="package-raw-dimensions"
                  data-testid="package-raw-dimensions"
                  value={form.raw_dimensions}
                  onChange={(e) => setField("raw_dimensions", e.target.value)}
                />
              </FormField>
            </div>

            <h3 className="section-subtitle">Medidas</h3>
            <div className="form-grid">
              <FormField label="Comprimento" htmlFor="package-length">
                <TextInput
                  id="package-length"
                  data-testid="package-length"
                  value={form.length}
                  onChange={(e) => setField("length", e.target.value)}
                />
              </FormField>
              <FormField label="Largura" htmlFor="package-width">
                <TextInput
                  id="package-width"
                  data-testid="package-width"
                  value={form.width}
                  onChange={(e) => setField("width", e.target.value)}
                />
              </FormField>
              <FormField label="Altura" htmlFor="package-height">
                <TextInput
                  id="package-height"
                  data-testid="package-height"
                  value={form.height}
                  onChange={(e) => setField("height", e.target.value)}
                />
              </FormField>
              <FormField label="Unidade de medida" htmlFor="package-dimension-unit">
                <SelectField
                  id="package-dimension-unit"
                  data-testid="package-dimension-unit"
                  value={form.dimension_unit}
                  onChange={(e) => setField("dimension_unit", e.target.value)}
                  options={DIMENSION_UNITS}
                />
              </FormField>
            </div>

            <h3 className="section-subtitle">Pesos</h3>
            <div className="form-grid">
              <FormField label="Peso líquido físico (kg)" htmlFor="package-net-weight">
                <TextInput
                  id="package-net-weight"
                  data-testid="package-net-weight"
                  value={form.net_weight_kg}
                  onChange={(e) => setField("net_weight_kg", e.target.value)}
                />
              </FormField>
              <FormField label="Peso bruto físico (kg)" htmlFor="package-gross-weight">
                <TextInput
                  id="package-gross-weight"
                  data-testid="package-gross-weight"
                  value={form.gross_weight_kg}
                  onChange={(e) => setField("gross_weight_kg", e.target.value)}
                />
              </FormField>
              <FormField label="Volume (m³)" htmlFor="package-volume" hint="Opcional">
                <TextInput
                  id="package-volume"
                  data-testid="package-volume"
                  value={form.volume_m3}
                  onChange={(e) => setField("volume_m3", e.target.value)}
                />
              </FormField>
            </div>

            <h3 className="section-subtitle">Origem documental</h3>
            <div className="form-grid">
              <FormField label="Documento de origem" htmlFor="package-source-document-id">
                <SelectField
                  id="package-source-document-id"
                  data-testid="package-source-document-id"
                  value={form.source_document_id}
                  onChange={(e) => setField("source_document_id", e.target.value)}
                  options={[{ value: "", label: "— nenhum —" }, ...docOptions]}
                />
              </FormField>
            </div>
            <div className="actions">
              {editId == null ? (
                <Button
                  type="button"
                  busy={busy}
                  data-testid="shipment-add-package"
                  onClick={() => onAddPackage(form)}
                >
                  Adicionar volume
                </Button>
              ) : (
                <>
                  <Button
                    type="button"
                    busy={busy}
                    data-testid="shipment-save-package"
                    onClick={() => onUpdatePackage(editId, form)}
                  >
                    Salvar volume #{editId}
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setEditId(null);
                      setForm(emptyPackageForm());
                    }}
                  >
                    Cancelar edição
                  </Button>
                </>
              )}
              <Button
                type="button"
                variant="secondary"
                busy={busy}
                data-testid="shipment-batch-homogeneous"
                onClick={() => onBatchHomogeneous(form)}
                aria-label="Criar grupo homogêneo com a quantidade de volumes do formulário"
              >
                Grupo homogêneo
              </Button>
            </div>
            <Notice tone="info" data-testid="batch-range-help">
              Intervalo CTNS: cria um volume para cada número de {rangeFrom || "…"} até {rangeTo || "…"}{" "}
              ({Math.max(0, (Number(rangeTo) || 0) - (Number(rangeFrom) || 0) + 1) || "—"} registros),
              reutilizando tipo, pesos, NCM da embalagem e demais atributos do formulário acima. Grupo
              homogêneo cria N volumes iguais sem numeração sequencial. Depois use a seleção na tabela
              para editar vários de uma vez.
            </Notice>
            <div className="form-grid">
              <FormField label="Número inicial (CTNS)" htmlFor="package-range-from">
                <TextInput
                  id="package-range-from"
                  data-testid="package-range-from"
                  value={rangeFrom}
                  onChange={(e) => setRangeFrom(e.target.value)}
                />
              </FormField>
              <FormField label="Número final (CTNS)" htmlFor="package-range-to">
                <TextInput
                  id="package-range-to"
                  data-testid="package-range-to"
                  value={rangeTo}
                  onChange={(e) => setRangeTo(e.target.value)}
                />
              </FormField>
            </div>
            <div className="actions">
              <Button
                type="button"
                busy={busy}
                data-testid="shipment-batch-range"
                onClick={() => onBatchRange(form, rangeFrom, rangeTo)}
                aria-label="Criar intervalo de volumes CTNS"
              >
                Criar intervalo (CTNS)
              </Button>
              <Button
                type="button"
                variant="secondary"
                busy={busy}
                disabled={selected.length === 0}
                data-testid="shipment-batch-update"
                onClick={() => onBatchUpdate(selected, form)}
                aria-label={`Editar ${selected.length} volumes selecionados`}
              >
                Editar selecionados ({selected.length})
              </Button>
            </div>
          </div>
        ) : null}

        {(shipment.packages?.length ?? 0) === 0 ? (
          <EmptyState message="Nenhum volume — embalagem sem conteúdo comercial é permitida" />
        ) : (
          <OperationalTable density="finance">
            <thead>
              <tr>
                {structureEditable ? <th></th> : null}
                <th>ID</th>
                <th>CTNS</th>
                <th>Tipo</th>
                <th className="num">Qtd</th>
                <th>NCM emb.</th>
                <th>Dims</th>
                <th>Peso líq.</th>
                <th>Peso bruto</th>
                <th>Vol.</th>
                <th scope="col">Conteúdo do volume</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {shipment.packages?.map((pkg) => (
                <tr key={pkg.id} data-testid={`package-row-${pkg.id}`}>
                  {structureEditable ? (
                    <td>
                      <input
                        type="checkbox"
                        data-testid={`package-select-${pkg.id}`}
                        checked={selected.includes(pkg.id)}
                        onChange={() => toggleSelect(pkg.id)}
                      />
                    </td>
                  ) : null}
                  <td>{pkg.id}</td>
                  <td>{pkg.external_package_no ?? "—"}</td>
                  <td>{pkg.package_type}</td>
                  <td className="num">{formatQuantity(String(pkg.package_count))}</td>
                  <td>{pkg.packaging_ncm ?? "—"}</td>
                  <td>
                    {pkg.raw_dimensions ||
                      (pkg.length
                        ? `${formatQuantity(pkg.length)}×${formatQuantity(pkg.width)}×${formatQuantity(pkg.height)} ${pkg.dimension_unit ?? ""}`.trim()
                        : "—")}
                  </td>
                  <td className="num">{formatQuantity(pkg.net_weight_kg)}</td>
                  <td className="num">{formatQuantity(pkg.gross_weight_kg)}</td>
                  <td className="num">
                    {formatQuantity(pkg.volume_m3)}
                    {pkg.volume_is_derived ? <span className="muted"> (der.)</span> : null}
                  </td>
                  <td>{pkg.contents?.length ?? 0}</td>
                  <td>
                    {structureEditable ? (
                      <div className="stack-row">
                        <Button type="button" variant="ghost" onClick={() => loadPackage(pkg)}>
                          Editar
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          data-testid={`shipment-edit-contents-${pkg.id}`}
                          onClick={() => openContents(pkg)}
                        >
                          Conteúdo
                        </Button>
                        <Button
                          type="button"
                          variant="ghost"
                          busy={busy}
                          data-testid={`shipment-remove-package-${pkg.id}`}
                          onClick={() => onRemovePackage(pkg.id)}
                        >
                          Remover
                        </Button>
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </OperationalTable>
        )}

        {contentsPkgId != null && structureEditable ? (
          <div className="stack" data-testid="package-contents-editor">
            <h3 className="section-subtitle" tabIndex={-1} id="package-contents-heading">
              Conteúdo do volume #{contentsPkgId}
            </h3>
            <Notice tone="info">
              NCM do produto é o da linha documental — não use o NCM da embalagem aqui. Pesos unitários e
              totais de linha são documentais e não substituem os pesos físicos do volume.
            </Notice>
            {contents.map((row, idx) => (
              <div className="stack" key={idx} data-testid={`content-row-${idx}`}>
                <div className="form-grid">
                  <FormField label="Item do embarque" htmlFor={`content-item-${idx}`}>
                    <SelectField
                      id={`content-item-${idx}`}
                      data-testid={`content-item-${idx}`}
                      value={row.shipment_item_id}
                      onChange={(e) => {
                        const v = e.target.value;
                        setContents((prev) =>
                          prev.map((r, i) => (i === idx ? { ...r, shipment_item_id: v } : r)),
                        );
                      }}
                      options={[{ value: "", label: "Selecionar item…" }, ...itemOptions]}
                    />
                  </FormField>
                  <FormField label="Quantidade alocada" htmlFor={`content-qty-${idx}`}>
                    <TextInput
                      id={`content-qty-${idx}`}
                      data-testid={`content-qty-${idx}`}
                      value={row.contained_quantity}
                      onChange={(e) => {
                        const v = e.target.value;
                        setContents((prev) =>
                          prev.map((r, i) => (i === idx ? { ...r, contained_quantity: v } : r)),
                        );
                      }}
                    />
                  </FormField>
                  <FormField label="Unidades por volume" htmlFor={`content-units-per-${idx}`}>
                    <TextInput
                      id={`content-units-per-${idx}`}
                      data-testid={`content-units-per-${idx}`}
                      value={row.units_per_package}
                      onChange={(e) => {
                        const v = e.target.value;
                        setContents((prev) =>
                          prev.map((r, i) => (i === idx ? { ...r, units_per_package: v } : r)),
                        );
                      }}
                    />
                  </FormField>
                  <FormField label="Unidade documental" htmlFor={`content-unit-${idx}`}>
                    <TextInput
                      id={`content-unit-${idx}`}
                      data-testid={`content-unit-${idx}`}
                      value={row.source_unit}
                      onChange={(e) => {
                        const v = e.target.value;
                        setContents((prev) =>
                          prev.map((r, i) => (i === idx ? { ...r, source_unit: v } : r)),
                        );
                      }}
                    />
                  </FormField>
                  <FormField label="NCM do produto" htmlFor={`content-ncm-${idx}`}>
                    <TextInput
                      id={`content-ncm-${idx}`}
                      data-testid={`content-ncm-${idx}`}
                      value={row.source_ncm}
                      onChange={(e) => {
                        const v = e.target.value;
                        setContents((prev) =>
                          prev.map((r, i) => (i === idx ? { ...r, source_ncm: v } : r)),
                        );
                      }}
                    />
                  </FormField>
                  <FormField label="Descrição documental" htmlFor={`content-desc-${idx}`} className="span-2">
                    <TextInput
                      id={`content-desc-${idx}`}
                      data-testid={`content-desc-${idx}`}
                      value={row.source_description}
                      onChange={(e) => {
                        const v = e.target.value;
                        setContents((prev) =>
                          prev.map((r, i) => (i === idx ? { ...r, source_description: v } : r)),
                        );
                      }}
                    />
                  </FormField>
                  <FormField label="Referência da linha no documento" htmlFor={`content-line-ref-${idx}`}>
                    <TextInput
                      id={`content-line-ref-${idx}`}
                      data-testid={`content-line-ref-${idx}`}
                      value={row.source_line_reference}
                      onChange={(e) => {
                        const v = e.target.value;
                        setContents((prev) =>
                          prev.map((r, i) => (i === idx ? { ...r, source_line_reference: v } : r)),
                        );
                      }}
                    />
                  </FormField>
                  <FormField label="Peso líquido unitário (kg)" htmlFor={`content-unit-net-${idx}`}>
                    <TextInput
                      id={`content-unit-net-${idx}`}
                      data-testid={`content-unit-net-${idx}`}
                      value={row.unit_net_weight_kg}
                      onChange={(e) => {
                        const v = e.target.value;
                        setContents((prev) =>
                          prev.map((r, i) => (i === idx ? { ...r, unit_net_weight_kg: v } : r)),
                        );
                      }}
                    />
                  </FormField>
                  <FormField label="Peso bruto unitário (kg)" htmlFor={`content-unit-gross-${idx}`}>
                    <TextInput
                      id={`content-unit-gross-${idx}`}
                      data-testid={`content-unit-gross-${idx}`}
                      value={row.unit_gross_weight_kg}
                      onChange={(e) => {
                        const v = e.target.value;
                        setContents((prev) =>
                          prev.map((r, i) => (i === idx ? { ...r, unit_gross_weight_kg: v } : r)),
                        );
                      }}
                    />
                  </FormField>
                  <FormField label="Peso líquido total da linha (kg)" htmlFor={`content-total-net-${idx}`}>
                    <TextInput
                      id={`content-total-net-${idx}`}
                      data-testid={`content-total-net-${idx}`}
                      value={row.source_total_net_weight_kg}
                      onChange={(e) => {
                        const v = e.target.value;
                        setContents((prev) =>
                          prev.map((r, i) =>
                            i === idx ? { ...r, source_total_net_weight_kg: v } : r,
                          ),
                        );
                      }}
                    />
                  </FormField>
                  <FormField label="Peso bruto total da linha (kg)" htmlFor={`content-total-gross-${idx}`}>
                    <TextInput
                      id={`content-total-gross-${idx}`}
                      data-testid={`content-total-gross-${idx}`}
                      value={row.source_total_gross_weight_kg}
                      onChange={(e) => {
                        const v = e.target.value;
                        setContents((prev) =>
                          prev.map((r, i) =>
                            i === idx ? { ...r, source_total_gross_weight_kg: v } : r,
                          ),
                        );
                      }}
                    />
                  </FormField>
                </div>
              </div>
            ))}
            <div className="actions">
              <Button
                type="button"
                variant="secondary"
                data-testid="content-add-row"
                onClick={() => setContents((p) => [...p, emptyContent()])}
              >
                Adicionar linha de conteúdo
              </Button>
              <Button
                type="button"
                busy={busy}
                data-testid="shipment-save-contents"
                onClick={() => onSaveContents(contentsPkgId, contents)}
              >
                Salvar conteúdos
              </Button>
              <Button type="button" variant="ghost" onClick={() => setContentsPkgId(null)}>
                Fechar
              </Button>
            </div>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard title="Documentos do embarque" data-testid="shipment-documents">
        <Notice tone="info">
          Totais declarados abaixo são referência por documento (origem do total declarado). Compare com os
          totais derivados na seção Totais.
        </Notice>
        {documents.length === 0 ? (
          <EmptyState message="Nenhum documento vinculado" />
        ) : (
          <OperationalTable density="finance">
            <thead>
              <tr>
                <th scope="col">Arquivo</th>
                <th scope="col">Papel</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((d) => (
                <tr key={d.id}>
                  <td>
                    <DocumentActions
                      documentId={d.id}
                      filename={d.original_filename}
                      mimeType={d.mime_type}
                      data-testid={`shipment-doc-actions-${d.id}`}
                    />
                  </td>
                  <td>{d.role ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </OperationalTable>
        )}
        {structureEditable ? (
          <FileUpload
            data-testid="shipment-doc-upload"
            label="Anexar Packing List / documento logístico"
            disabled={uploadBusy}
            onFileChange={(file) => {
              if (file) void onUpload(file);
            }}
          />
        ) : null}

        {structureEditable ? (
          <div className="stack" data-testid="document-summary-editor">
            <h3 className="section-subtitle">Resumo declarado</h3>
            <Notice tone="info">
              Informe os totais que o documento declara (peso, volumes, paletes). Isso não altera os totais
              derivados dos volumes físicos.
            </Notice>
            <div className="form-grid">
              <FormField label="Documento" htmlFor="summary-document-id">
                <SelectField
                  id="summary-document-id"
                  data-testid="summary-document-id"
                  value={summary.document_id}
                  onChange={(e) => setSummary((s) => ({ ...s, document_id: e.target.value }))}
                  options={[{ value: "", label: "Selecionar documento…" }, ...docOptions]}
                />
              </FormField>
              <FormField label="Origem do total declarado" htmlFor="summary-provenance">
                <SelectField
                  id="summary-provenance"
                  data-testid="summary-provenance"
                  value={summary.declared_provenance}
                  onChange={(e) => setSummary((s) => ({ ...s, declared_provenance: e.target.value }))}
                  options={PROVENANCE_OPTIONS}
                />
              </FormField>
              <FormField label="Peso líquido declarado (kg)" htmlFor="summary-net">
                <TextInput
                  id="summary-net"
                  data-testid="summary-net"
                  value={summary.declared_net_weight_kg}
                  onChange={(e) => setSummary((s) => ({ ...s, declared_net_weight_kg: e.target.value }))}
                />
              </FormField>
              <FormField label="Peso bruto declarado (kg)" htmlFor="summary-gross">
                <TextInput
                  id="summary-gross"
                  data-testid="summary-gross"
                  value={summary.declared_gross_weight_kg}
                  onChange={(e) =>
                    setSummary((s) => ({ ...s, declared_gross_weight_kg: e.target.value }))
                  }
                />
              </FormField>
              <FormField label="Paletes declarados" htmlFor="summary-pallets">
                <TextInput
                  id="summary-pallets"
                  data-testid="summary-pallets"
                  value={summary.declared_pallet_count}
                  onChange={(e) =>
                    setSummary((s) => ({ ...s, declared_pallet_count: e.target.value }))
                  }
                />
              </FormField>
              <FormField label="Caixas declaradas" htmlFor="summary-cartons">
                <TextInput
                  id="summary-cartons"
                  data-testid="summary-cartons"
                  value={summary.declared_carton_count}
                  onChange={(e) =>
                    setSummary((s) => ({ ...s, declared_carton_count: e.target.value }))
                  }
                />
              </FormField>
              <FormField label="Volume declarado (m³)" htmlFor="summary-volume">
                <TextInput
                  id="summary-volume"
                  data-testid="summary-volume"
                  value={summary.declared_volume_m3}
                  onChange={(e) => setSummary((s) => ({ ...s, declared_volume_m3: e.target.value }))}
                />
              </FormField>
              <FormField label="Notas" htmlFor="summary-notes" className="span-2">
                <TextInput
                  id="summary-notes"
                  data-testid="summary-notes"
                  value={summary.raw_notes}
                  onChange={(e) => setSummary((s) => ({ ...s, raw_notes: e.target.value }))}
                />
              </FormField>
            </div>
            <Button
              type="button"
              busy={busy}
              data-testid="shipment-save-summary"
              onClick={() => onSaveSummary(summary)}
            >
              Salvar resumo declarado
            </Button>
          </div>
        ) : null}

        {(shipment.document_summaries?.length ?? 0) === 0 ? (
          <EmptyState message="Nenhum resumo documental" />
        ) : (
          <OperationalTable density="finance">
            <thead>
              <tr>
                <th>Documento</th>
                <th>Origem do total declarado</th>
                <th className="num">Peso líq.</th>
                <th className="num">Peso bruto</th>
                <th className="num">Paletes</th>
                <th className="num">Caixas</th>
                <th className="num">Volume</th>
              </tr>
            </thead>
            <tbody>
              {shipment.document_summaries?.map((s) => (
                <tr key={s.id}>
                  <td>#{s.document_id}</td>
                  <td>
                    {s.declared_provenance
                      ? (PROVENANCE_LABEL[s.declared_provenance] ?? s.declared_provenance)
                      : "—"}
                  </td>
                  <td className="num">{formatQuantity(s.declared_net_weight_kg)}</td>
                  <td className="num">{formatQuantity(s.declared_gross_weight_kg)}</td>
                  <td className="num">
                    {s.declared_pallet_count != null ? String(s.declared_pallet_count) : "—"}
                  </td>
                  <td className="num">
                    {s.declared_carton_count != null ? String(s.declared_carton_count) : "—"}
                  </td>
                  <td className="num">{formatQuantity(s.declared_volume_m3)}</td>
                </tr>
              ))}
            </tbody>
          </OperationalTable>
        )}
      </SectionCard>
    </>
  );
}

export function packageFormToBody(form: PackageFormState) {
  const empty = (v: string) => (v.trim() === "" ? null : v.trim());
  return {
    package_type: form.package_type,
    package_count: Number(form.package_count) || 1,
    external_package_no: empty(form.external_package_no),
    description: empty(form.description),
    packaging_ncm: empty(form.packaging_ncm),
    length: empty(form.length),
    width: empty(form.width),
    height: empty(form.height),
    dimension_unit: empty(form.dimension_unit),
    raw_dimensions: empty(form.raw_dimensions),
    net_weight_kg: empty(form.net_weight_kg),
    gross_weight_kg: empty(form.gross_weight_kg),
    volume_m3: empty(form.volume_m3),
    parent_package_id: form.parent_package_id ? Number(form.parent_package_id) : null,
    source_document_id: form.source_document_id ? Number(form.source_document_id) : null,
  };
}

export function contentDraftsToBody(contents: ContentDraft[]) {
  return contents
    .filter((c) => c.shipment_item_id)
    .map((c) => {
      const empty = (v: string) => (v.trim() === "" ? null : v.trim());
      return {
        shipment_item_id: Number(c.shipment_item_id),
        contained_quantity: empty(c.contained_quantity),
        source_unit: empty(c.source_unit),
        source_line_reference: empty(c.source_line_reference),
        source_ncm: empty(c.source_ncm),
        source_description: empty(c.source_description),
        units_per_package: empty(c.units_per_package),
        unit_net_weight_kg: empty(c.unit_net_weight_kg),
        unit_gross_weight_kg: empty(c.unit_gross_weight_kg),
        source_total_net_weight_kg: empty(c.source_total_net_weight_kg),
        source_total_gross_weight_kg: empty(c.source_total_gross_weight_kg),
      };
    });
}
