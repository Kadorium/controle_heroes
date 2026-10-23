import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import {
  fetchTaxonomy,
  getProduct,
  patchProduct,
  fetchProductAttributeValues,
  type Product,
  type Taxonomy,
} from "./catalogApi";
import { classificationLine, humanValue, productIdentity } from "./productIdentity";
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
  SelectField,
  TextInput,
  type AuditEntry,
} from "../../ui";

import { SalesPrices } from "./SalesPrices";

type Props = { user: User; editing?: boolean };

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("catalog:write");
}

function Pair({ label, value, wide = false }: { label: string; value: string; wide?: boolean }) {
  const empty = value === "Não informado";
  return (
    <div className={wide ? "pair pair-wide" : "pair"}>
      <dt>{label}</dt>
      <dd className={empty ? "is-empty" : undefined}>{value}</dd>
    </div>
  );
}

export function ProductDetailPage({ user, editing = false }: Props) {
  const { productId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const listReturn =
    (location.state as { returnTo?: string } | null)?.returnTo || buildReturnTo("/catalog/products");
  const id = Number(productId);
  const write = canWrite(user);
  const [row, setRow] = useState<Product | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [taxonomy, setTaxonomy] = useState<Taxonomy | null>(null);
  const [commercialName, setCommercialName] = useState("");
  const [shortDescription, setShortDescription] = useState("");
  const [size, setSize] = useState("");
  const [color, setColor] = useState("");
  const [ncm, setNcm] = useState("");
  const [ean, setEan] = useState("");
  const [origin, setOrigin] = useState("");
  const [unit, setUnit] = useState("");
  const [weight, setWeight] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [typeId, setTypeId] = useState("");
  const [subcategory, setSubcategory] = useState("");
  const [sport, setSport] = useState("");
  const [model, setModel] = useState("");
  const [collectionYear, setCollectionYear] = useState("");
  const [line, setLine] = useState("");
  const [consumableKind,setConsumableKind]=useState("");
  const [garmentKind, setGarmentKind] = useState("");
  const [gender, setGender] = useState("");
  const [supplierSku, setSupplierSku] = useState("");
  const [sizeHints, setSizeHints] = useState<string[]>([]);
  const [colorHints, setColorHints] = useState<string[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [typeNotice, setTypeNotice] = useState<string | null>(null);
  const [pendenciesOpen, setPendenciesOpen] = useState(false);

  function hydrate(p: Product) {
    setRow(p);
    setCommercialName(p.commercial_name || p.description);
    setShortDescription(p.short_description ?? "");
    setSize(p.size ?? "");
    setColor(p.color ?? "");
    setNcm(p.ncm ?? "");
    setEan(p.ean ?? "");
    setOrigin(p.country_of_origin ?? "");
    setUnit(p.unit ?? "");
    setWeight(p.net_weight_kg != null ? String(p.net_weight_kg) : "");
    setCategoryId(p.category_id != null ? String(p.category_id) : "");
    setTypeId(p.product_type_id != null ? String(p.product_type_id) : "");
    setSubcategory(p.subcategory ?? "");
    setSport(p.sport ?? "");
    setModel(p.model ?? "");
    setCollectionYear(p.collection_year ?? "");
    setLine(p.line ?? "");
    setGarmentKind(p.garment_kind ?? "");
    setConsumableKind(String(p.attributes?.consumable_kind||""));
    setGender(p.gender ?? "");
    setSupplierSku(p.supplier_sku ?? "");
  }

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    let cancelled = false;
    void (async () => {
      try {
        const p = await getProduct(id);
        if (cancelled) return;
        hydrate(p);
        const [sizes, colors, tax] = await Promise.all([
          fetchProductAttributeValues("size").catch(() => []),
          fetchProductAttributeValues("color").catch(() => []),
          fetchTaxonomy().catch(() => null),
        ]);
        if (!cancelled) {
          setSizeHints(sizes);
          setColorHints(colors);
          if (tax) setTaxonomy(tax);
        }
        const events = await listEntityAudit("product", String(id));
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

  if (!Number.isFinite(id)) return <ErrorState message="Produto inválido." />;
  if (error && !row) return <ErrorState message={error} />;
  if (!row) return <LoadingState message="Carregando produto…" />;

  const idn = productIdentity(row);
  const selectedCat = taxonomy?.categories.find((c) => String(c.id) === categoryId);
  const typeOptions = (taxonomy?.product_types ?? []).map((t) => ({ value: String(t.id), label: t.name }));
  const catOptions = (taxonomy?.categories ?? []).map((c) => ({ value: String(c.id), label: c.name }));
  const subOptions = (selectedCat?.subcategories ?? []).map((name) => ({ value: name, label: name }));

  async function save(extra?: { is_active?: boolean }) {
    if (busy || !row) return;
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const updated = await patchProduct(row.id, {
        commercial_name: commercialName.trim(),
        short_description: shortDescription.trim() || null,
        size: size.trim() || null,
        color: color.trim() || null,
        ncm: ncm.trim() || null,
        ean: ean.trim() || null,
        country_of_origin: origin.trim() || null,
        unit: unit.trim() || null,
        net_weight_kg: weight.trim() ? weight.trim() : null,
        supplier_sku: supplierSku.trim() || null,
        category_id: categoryId ? Number(categoryId) : null,
        product_type_id: typeId ? Number(typeId) : null,
        subcategory: subcategory.trim() || null,
        attributes: {
          sport: sport.trim() || null,
          model: model.trim() || null,
          collection_year: collectionYear.trim() || null,
          line: line.trim() || null,
          garment_kind: garmentKind.trim() || null,
          consumable_kind: consumableKind || null,
          gender: gender.trim() || null,
        },
        ...extra,
        is_active: extra?.is_active ?? row.is_active,
      });
      hydrate(updated);
      if (updated.notices?.length) setTypeNotice(updated.notices[0] ?? null);
      setNotice("Alterações gravadas.");
      return updated;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
      return null;
    } finally {
      setBusy(false);
    }
  }

  if (!editing) {
    const quality = row.quality;
    return (
      <section className="panel dense" data-testid="product-detail-page">
        <ContextBreadcrumb items={[{ label: "Produtos", to: listReturn }, { label: idn.title }]} />
        <PageHeader
          title={idn.title}
          subtitle={`${classificationLine(row) || "Sem classificação"} · ${row.sku}`}
          actions={
            <>
              <Link className="ui-button ui-button--secondary" to={listReturn} data-testid="product-back">
                Voltar à lista
              </Link>
              {write ? (
                <Button
                  type="button"
                  variant="secondary"
                  busy={busy}
                  data-testid="product-toggle-active"
                  onClick={() => void save({ is_active: !row.is_active })}
                >
                  {row.is_active ? "Inativar" : "Reativar"}
                </Button>
              ) : null}
              {write ? (
                <Link className="ui-button" to={`/catalog/products/${row.id}/edit`} data-testid="product-edit">
                  Editar
                </Link>
              ) : null}
            </>
          }
        />
        <div className="product-hero">
          <div className="product-thumb product-thumb--lg" aria-hidden="true">
            <span>Placeholder — não é foto oficial</span>
          </div>
          <div>
            <div className="stack-row" style={{ gap: "0.5rem", marginBottom: "0.5rem", flexWrap: "wrap" }}>
              {row.is_active ? (
                <span className="status-badge status-ok">Ativo</span>
              ) : (
                <span className="status-badge status-neutral">Inativo</span>
              )}
              {row.needs_classification_review ? <span className="status-badge status-warn">Revisar classificação</span> : null}
              {row.needs_review && !row.needs_classification_review ? (
                <span className="status-badge status-warn">Precisa revisar</span>
              ) : null}
            </div>
            <p className="product-hero-name">{idn.title}</p>
          </div>
        </div>
        <nav className="object-anchors" aria-label="Seções da ficha">
          <a href="#identidade">Identidade</a>
          <a href="#classificacao">Classificação</a>
          <a href="#qualidade">Qualidade</a>
          <a href="#fiscal">Fiscal</a>
          <a href="#comercial">Comercial</a>
          <a href="#origem">Origem da informação</a>
        </nav>
        {idn.fallback ? (
          <Notice tone="warning">Sem descrição comercial — o SKU é a única identidade humana disponível neste registro.</Notice>
        ) : null}
        {notice ? <Notice tone="info">{notice}</Notice> : null}
        {error ? (
          <Notice tone="danger" className="error">
            {error}
          </Notice>
        ) : null}
        <div className="object-sheet object-page">
          <section className="object-section tight" id="identidade">
            <h2>Identidade e características</h2>
            <div className="pair-grid">
              <Pair label="Esporte" value={humanValue(row.sport)} />
              <Pair label="Modelo" value={humanValue(row.model)} />
              <Pair label="Coleção" value={humanValue(row.collection_year)} />
              <Pair label="Cor" value={humanValue(row.color)} />
              {row.line ? <Pair label="Linha" value={row.line} /> : null}
              {row.garment_kind ? <Pair label="Peça" value={row.garment_kind} /> : null}
              {row.gender ? <Pair label="Gênero" value={row.gender} /> : null}
            </div>
          </section>
          <section className="object-section tight" id="classificacao">
            <h2>Classificação</h2>
            {row.classification_note ? <p className="muted tiny">{row.classification_note}</p> : null}
            {row.needs_classification_review && row.taxonomy_reason ? (
              <p className="muted tiny">{row.taxonomy_reason}</p>
            ) : null}
            <div className="pair-grid">
              <Pair label="Categoria" value={humanValue(row.category_name)} />
              <Pair label="Subcategoria" value={humanValue(row.subcategory)} />
              <Pair label="Tipo" value={humanValue(row.product_type_name)} />
            </div>
          </section>
          <section className="object-section tight" id="qualidade">
            <h2>Qualidade do cadastro</h2>
            <div className="quality-compact">
              <strong>{quality?.summary || "—"}</strong>
              <Button type="button" variant="ghost" data-testid="product-pendencies" onClick={() => setPendenciesOpen((v) => !v)}>
                {pendenciesOpen ? "Ocultar pendências" : "Ver pendências"}
              </Button>
            </div>
            {pendenciesOpen && quality?.items ? (
              <ul className="quality-list" data-testid="product-quality-list">
                {quality.items.map((item) => (
                  <li key={item.code} className={item.ok ? "is-ok" : "is-gap"}>
                    {item.ok ? item.label : `${item.label} — ${item.consequence}`}
                  </li>
                ))}
              </ul>
            ) : null}
          </section>
          <section className="object-section tight" id="fiscal">
            <h2>Fiscal e logística</h2>
            <div className="pair-grid">
              <Pair label="NCM" value={humanValue(row.ncm)} />
              <Pair label="Descrição fiscal" value={humanValue(row.fiscal_description)} />
              <Pair label="Origem" value={humanValue(row.country_of_origin)} />
              <Pair label="Unidade" value={humanValue(row.unit)} />
              <Pair label="EAN" value={humanValue(row.ean)} />
              <Pair label="Peso líquido (kg)" value={humanValue(row.net_weight_kg)} />
            </div>
          </section>
          <section className="object-section tight" id="comercial">
            <h2>Comercial</h2>
            <div className="pair-grid">
              <Pair label="Código do fornecedor" value={humanValue(row.supplier_sku)} />
              <Pair label="Descrição curta" value={humanValue(row.short_description)} wide />
            </div>
          </section>
          <section className="object-section tight" id="origem">
            <h2>Origem da informação</h2>
            {row.provenance?.length ? (
              <div className="pair-grid">
                {row.provenance.map((entry) => (
                  <Pair key={entry.field} label={entry.label} value={entry.source_label} />
                ))}
              </div>
            ) : (
              <p className="muted">Sem histórico de origem além da criação manual.</p>
            )}
          </section>
        </div>
        <SalesPrices productId={id} unit={row.unit||null} user={user}/>
        <AuditDocumentsBlock documents={[]} audit={audit} documentsTitle="Histórico" />
      </section>
    );
  }

  return (
    <section className="panel dense" data-testid="product-edit-page">
      <ContextBreadcrumb
        items={[
          { label: "Produtos", to: listReturn },
          { label: idn.title, to: `/catalog/products/${row.id}` },
          { label: "Editar" },
        ]}
      />
      <PageHeader
        title="Editar produto"
        subtitle={row.sku}
        actions={
          <Link className="ui-button ui-button--secondary" to={`/catalog/products/${row.id}`}>
            Cancelar
          </Link>
        }
      />
      {error ? (
        <Notice tone="danger" className="error">
          {error}
        </Notice>
      ) : null}
      {typeNotice ? <Notice tone="warning">{typeNotice}</Notice> : null}
      {notice ? <Notice tone="info">{notice}</Notice> : null}
      <form
        className="object-sheet object-page"
        data-testid="product-edit-form"
        onSubmit={(e) => {
          e.preventDefault();
          void save().then((updated) => {
            if (updated) navigate(`/catalog/products/${updated.id}`);
          });
        }}
      >
        <section className="object-section">
          <h2>Essenciais</h2>
          <div className="form-grid object-form">
            <FormField label="SKU" htmlFor="p-sku" className="field-sku">
              <TextInput id="p-sku" value={row.sku} readOnly />
            </FormField>
            <FormField label="Nome comercial" htmlFor="p-desc" required className="span-2">
              <TextInput
                id="p-desc"
                data-testid="product-description"
                value={commercialName}
                onChange={(e) => setCommercialName(e.target.value)}
                disabled={!write}
              />
            </FormField>
            <FormField label="Situação" htmlFor="p-active">
              <SelectField
                id="p-active"
                value={row.is_active ? "1" : "0"}
                onChange={(e) => setRow({ ...row, is_active: e.target.value === "1" })}
                options={[
                  { value: "1", label: "Ativo" },
                  { value: "0", label: "Inativo" },
                ]}
              />
            </FormField>
          </div>
        </section>
        <section className="object-section">
          <h2>Classificação</h2>
          <div className="form-grid object-form">
            <FormField label="Categoria" htmlFor="p-cat">
              <SelectField
                id="p-cat"
                value={categoryId}
                onChange={(e) => {
                  setCategoryId(e.target.value);
                  setSubcategory("");
                }}
                options={[{ value: "", label: "—" }, ...catOptions]}
              />
            </FormField>
            <FormField label="Tipo" htmlFor="p-type">
              <SelectField
                id="p-type"
                data-testid="product-type"
                value={typeId}
                onChange={(e) => {
                  if (typeId && e.target.value !== typeId) {
                    setTypeNotice(
                      "Algumas informações preenchidas não são usadas neste tipo de produto. Elas serão preservadas até você revisar.",
                    );
                  }
                  setTypeId(e.target.value);
                }}
                options={[{ value: "", label: "—" }, ...typeOptions]}
              />
            </FormField>
            {subOptions.length ? (
              <FormField label="Subcategoria" htmlFor="p-sub">
                <SelectField
                  id="p-sub"
                  value={subcategory}
                  onChange={(e) => setSubcategory(e.target.value)}
                  options={[{ value: "", label: "—" }, ...subOptions]}
                />
              </FormField>
            ) : null}
          </div>
        </section>
        <section className="object-section">
          <h2>Características</h2>
          <div className="form-grid object-form">
            <FormField label="Esporte" htmlFor="p-sport">
              <TextInput id="p-sport" value={sport} onChange={(e) => setSport(e.target.value)} disabled={!write} />
            </FormField>
            <FormField label="Modelo" htmlFor="p-model">
              <TextInput id="p-model" value={model} onChange={(e) => setModel(e.target.value)} disabled={!write} />
            </FormField>
            <FormField label="Coleção" htmlFor="p-year">
              <TextInput id="p-year" value={collectionYear} onChange={(e) => setCollectionYear(e.target.value)} disabled={!write} />
            </FormField>
            <FormField label="Linha" htmlFor="p-line">
              <TextInput id="p-line" value={line} onChange={(e) => setLine(e.target.value)} disabled={!write} />
            </FormField>
            <FormField label="Tipo de consumível" htmlFor="p-consumable"><SelectField id="p-consumable" value={consumableKind} onChange={e=>setConsumableKind(e.target.value)} disabled={!write} options={[{value:"",label:"Não informado"},{value:"BALL",label:"Bolas"},{value:"OVERGRIP",label:"Overgrips"},{value:"OTHER",label:"Outros"}]}/></FormField>
            <FormField label="Peça" htmlFor="p-piece">
              <TextInput id="p-piece" value={garmentKind} onChange={(e) => setGarmentKind(e.target.value)} disabled={!write} />
            </FormField>
            <FormField label="Gênero" htmlFor="p-gender">
              <TextInput id="p-gender" value={gender} onChange={(e) => setGender(e.target.value)} disabled={!write} />
            </FormField>
            <FormField label="Tamanho" htmlFor="p-size" className="field-short">
              <TextInput id="p-size" data-testid="product-size" value={size} list="product-size-list" onChange={(e) => setSize(e.target.value)} disabled={!write} />
              <datalist id="product-size-list">
                {sizeHints.map((v) => (
                  <option key={v} value={v} />
                ))}
              </datalist>
            </FormField>
            <FormField label="Cor" htmlFor="p-color" className="field-short">
              <TextInput id="p-color" data-testid="product-color" value={color} list="product-color-list" onChange={(e) => setColor(e.target.value)} disabled={!write} />
              <datalist id="product-color-list">
                {colorHints.map((v) => (
                  <option key={v} value={v} />
                ))}
              </datalist>
            </FormField>
          </div>
        </section>
        <section className="object-section">
          <h2>Comercial</h2>
          <div className="form-grid object-form">
            <FormField label="Descrição curta" htmlFor="p-short" className="span-2">
              <TextInput id="p-short" value={shortDescription} onChange={(e) => setShortDescription(e.target.value)} disabled={!write} />
            </FormField>
            <FormField label="Código do fornecedor" htmlFor="p-sup">
              <TextInput id="p-sup" value={supplierSku} onChange={(e) => setSupplierSku(e.target.value)} disabled={!write} />
            </FormField>
          </div>
        </section>
        <section className="object-section">
          <h2>Fiscal e logística</h2>
          <div className="form-grid object-form">
            <FormField label="NCM" htmlFor="p-ncm" hint="Oito dígitos; pontos são ignorados" className="field-short">
              <TextInput id="p-ncm" data-testid="product-ncm" value={ncm} onChange={(e) => setNcm(e.target.value)} disabled={!write} />
            </FormField>
            <FormField label="EAN" htmlFor="p-ean" className="field-ean">
              <TextInput id="p-ean" data-testid="product-ean" value={ean} onChange={(e) => setEan(e.target.value)} disabled={!write} />
            </FormField>
            <FormField label="Origem (ISO-2)" htmlFor="p-origin" className="field-short">
              <TextInput id="p-origin" data-testid="product-origin" value={origin} onChange={(e) => setOrigin(e.target.value)} disabled={!write} />
            </FormField>
            <FormField label="Unidade" htmlFor="p-unit" className="field-short">
              <TextInput id="p-unit" data-testid="product-unit" value={unit} onChange={(e) => setUnit(e.target.value)} disabled={!write} />
            </FormField>
            <FormField label="Peso líquido (kg)" htmlFor="p-weight" className="field-weight">
              <TextInput id="p-weight" data-testid="product-weight" value={weight} onChange={(e) => setWeight(e.target.value)} disabled={!write} />
            </FormField>
          </div>
        </section>
        {write ? (
          <div className="actions">
            <Button type="submit" busy={busy} data-testid="product-save">
              Salvar
            </Button>
          </div>
        ) : null}
      </form>
    </section>
  );
}
