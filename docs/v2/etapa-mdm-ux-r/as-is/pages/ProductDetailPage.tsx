import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import type { User } from "../auth/types";
import { getProduct, patchProduct, fetchProductAttributeValues, type Product } from "./catalogApi";
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

export function ProductDetailPage({ user }: Props) {
  const { productId } = useParams();
  const location = useLocation();
  const listReturn =
    (location.state as { returnTo?: string } | null)?.returnTo || buildReturnTo("/catalog/products");
  const id = Number(productId);
  const write = canWrite(user);
  const [row, setRow] = useState<Product | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [description, setDescription] = useState("");
  const [size, setSize] = useState("");
  const [color, setColor] = useState("");
  const [ncm, setNcm] = useState("");
  const [ean, setEan] = useState("");
  const [origin, setOrigin] = useState("");
  const [unit, setUnit] = useState("");
  const [weight, setWeight] = useState("");
  const [sizeHints, setSizeHints] = useState<string[]>([]);
  const [colorHints, setColorHints] = useState<string[]>([]);

  useEffect(() => {
    if (!Number.isFinite(id)) return;
    let cancelled = false;
    void (async () => {
      try {
        const p = await getProduct(id);
        if (cancelled) return;
        setRow(p);
        setDescription(p.description);
        setSize(p.size ?? "");
        setColor(p.color ?? "");
        setNcm(p.ncm ?? "");
        setEan(p.ean ?? "");
        setOrigin(p.country_of_origin ?? "");
        setUnit(p.unit ?? "");
        setWeight(p.net_weight_kg != null ? String(p.net_weight_kg) : "");
        const [sizes, colors] = await Promise.all([
          fetchProductAttributeValues("size").catch(() => []),
          fetchProductAttributeValues("color").catch(() => []),
        ]);
        if (!cancelled) {
          setSizeHints(sizes);
          setColorHints(colors);
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
  if (error) return <ErrorState message={error} />;
  if (!row) return <LoadingState message="Carregando produto…" />;

  async function save(extra?: { is_active?: boolean }) {
    if (busy || !row) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await patchProduct(row.id, {
        description: description.trim(),
        size: size.trim() || null,
        color: color.trim() || null,
        ncm: ncm.trim() || null,
        ean: ean.trim() || null,
        country_of_origin: origin.trim() || null,
        unit: unit.trim() || null,
        net_weight_kg: weight.trim() ? weight.trim() : null,
        ...extra,
      });
      setRow(updated);
      setDescription(updated.description);
      setSize(updated.size ?? "");
      setColor(updated.color ?? "");
      setNcm(updated.ncm ?? "");
      setEan(updated.ean ?? "");
      setOrigin(updated.country_of_origin ?? "");
      setUnit(updated.unit ?? "");
      setWeight(updated.net_weight_kg != null ? String(updated.net_weight_kg) : "");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro ao salvar");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel dense" data-testid="product-detail-page">
      <ContextBreadcrumb items={[{ label: "Produtos", to: listReturn }, { label: row.sku }]} />
      <PageHeader
        title={row.sku}
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
                data-testid="product-toggle-active"
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
      <SectionCard title="Visão geral">
        <div className="form-grid">
          <FormField label="SKU" htmlFor="p-sku">
            <TextInput id="p-sku" value={row.sku} readOnly />
          </FormField>
          <FormField label="Descrição" htmlFor="p-desc" required className="span-2">
            <TextInput
              id="p-desc"
              data-testid="product-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={!write}
            />
          </FormField>
        </div>
      </SectionCard>
      <SectionCard title="Características">
        <div className="form-grid">
          <FormField label="Tamanho" htmlFor="p-size">
            <TextInput
              id="p-size"
              data-testid="product-size"
              value={size}
              list="product-size-list"
              onChange={(e) => setSize(e.target.value)}
              disabled={!write}
            />
            <datalist id="product-size-list">
              {sizeHints.map((v) => (
                <option key={v} value={v} />
              ))}
            </datalist>
          </FormField>
          <FormField label="Cor" htmlFor="p-color">
            <TextInput
              id="p-color"
              data-testid="product-color"
              value={color}
              list="product-color-list"
              onChange={(e) => setColor(e.target.value)}
              disabled={!write}
            />
            <datalist id="product-color-list">
              {colorHints.map((v) => (
                <option key={v} value={v} />
              ))}
            </datalist>
          </FormField>
        </div>
      </SectionCard>
      <SectionCard title="Fiscal / aduana">
        <div className="form-grid">
          <FormField label="NCM" htmlFor="p-ncm" hint="Oito dígitos; pontos são ignorados">
            <TextInput
              id="p-ncm"
              data-testid="product-ncm"
              value={ncm}
              onChange={(e) => setNcm(e.target.value)}
              disabled={!write}
            />
          </FormField>
          <FormField label="EAN" htmlFor="p-ean">
            <TextInput
              id="p-ean"
              data-testid="product-ean"
              value={ean}
              onChange={(e) => setEan(e.target.value)}
              disabled={!write}
            />
          </FormField>
          <FormField label="Origem (ISO-2)" htmlFor="p-origin">
            <TextInput
              id="p-origin"
              data-testid="product-origin"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              disabled={!write}
            />
          </FormField>
          <FormField label="Unidade" htmlFor="p-unit">
            <TextInput
              id="p-unit"
              data-testid="product-unit"
              value={unit}
              onChange={(e) => setUnit(e.target.value)}
              disabled={!write}
            />
          </FormField>
        </div>
      </SectionCard>
      <SectionCard title="Físico">
        <FormField label="Peso líquido (kg)" htmlFor="p-weight">
          <TextInput
            id="p-weight"
            data-testid="product-weight"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            disabled={!write}
          />
        </FormField>
      </SectionCard>
      {write ? (
        <div className="actions">
          <Button type="button" busy={busy} data-testid="product-save" onClick={() => void save()}>
            Salvar
          </Button>
        </div>
      ) : null}
      <AuditDocumentsBlock documents={[]} audit={audit} documentsTitle="Documentos" />
    </section>
  );
}
