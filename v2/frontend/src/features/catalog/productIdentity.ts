import type { Product } from "./catalogApi";

const GENERIC = /^(item|produto|sku)[\s\-_.]*$/i;

export type ProductIdentity = {
  title: string;
  sub: string;
  fallback: boolean;
};

function commercialName(product: Product): string {
  return (product.commercial_name || product.description || "").trim();
}

/** DEC-MDM-HUMAN-IDENTITY: pessoa = nome comercial; senão SKU uma vez + rótulo. */
export function productIdentity(product: Product): ProductIdentity {
  const sku = product.sku?.trim() || "";
  const name = commercialName(product);
  const useless =
    !name ||
    name.localeCompare(sku, undefined, { sensitivity: "accent" }) === 0 ||
    GENERIC.test(name);
  if (useless) {
    return { title: sku || "—", sub: "Sem descrição comercial", fallback: true };
  }
  const bits: string[] = [sku];
  const klass = [product.category_name, product.subcategory].filter(Boolean).join(" › ");
  if (klass) bits.unshift(klass);
  if (product.product_type_name) bits.push(product.product_type_name);
  return { title: name, sub: bits.join(" · "), fallback: false };
}

export function productIncomplete(product: Product): boolean {
  if (product.quality?.quality_incomplete != null) return product.quality.quality_incomplete;
  return !product.ncm || !product.ean;
}

export function humanValue(value: string | number | null | undefined): string {
  if (value === null || value === undefined || String(value).trim() === "") return "Não informado";
  return String(value);
}

export function classificationLine(product: Product): string {
  const path = [product.category_name, product.subcategory].filter(Boolean).join(" › ");
  const type = product.product_type_name;
  if (path && type) return `${path} · ${type}`;
  return path || type || "";
}

export function displayTitle(product: Product): string {
  return productIdentity(product).title;
}

export function pickerCaption(product: Product): string {
  const name = (product.commercial_name || product.description || "").trim();
  const klass = [product.category_name, product.product_type_name].filter(Boolean).join(" · ");
  return klass ? `${name} · ${klass}` : name;
}

/** Código de barras (GTIN/EAN) não é SKU. */
export function skuLooksLikeGtin(sku: string | null | undefined): boolean {
  return /^\d{8,14}$/.test((sku || "").trim());
}

export const SKU_IS_EAN_MESSAGE =
  "SKU não pode ser o código de barras (EAN). Use o SKU canônico ou um código de ensaio e grave o EAN no campo EAN.";

export function matchCatalogProduct(products: Product[], query: string): Product | undefined {
  const q = query.trim().toLowerCase();
  if (!q) return undefined;
  const nameOf = (p: Product) => (p.commercial_name || p.description || "").trim().toLowerCase();
  const exactSku = products.find((p) => p.sku.toLowerCase() === q);
  if (exactSku) return exactSku;
  const exactEan = products.find((p) => (p.ean || "").trim() === query.trim());
  if (exactEan) return exactEan;
  const exactName = products.find((p) => nameOf(p) === q);
  if (exactName) return exactName;
  const contains = products.filter(
    (p) =>
      nameOf(p).includes(q) ||
      p.sku.toLowerCase().includes(q) ||
      (p.ean || "").toLowerCase().includes(q),
  );
  return contains.length === 1 ? contains[0] : undefined;
}
