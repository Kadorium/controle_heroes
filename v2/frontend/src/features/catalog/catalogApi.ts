import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type Supplier = components["schemas"]["SupplierResponse"];
export type Product = components["schemas"]["ProductResponse"];
export type ProductList = components["schemas"]["ProductListResponse"];
export type ProductListSummary = components["schemas"]["ProductListSummary"];
export type SupplierList = components["schemas"]["SupplierListResponse"];
export type ProductPatch = components["schemas"]["ProductPatch"];
export type SupplierPatch = components["schemas"]["SupplierPatch"];
export type Taxonomy = components["schemas"]["TaxonomyResponse"];

function errMsg(error: unknown, fallback: string) {
  return (error as { message?: string } | undefined)?.message || fallback;
}

export type CatalogListOpts = {
  activeOnly?: boolean;
  limit?: number;
  offset?: number;
};

export async function listSuppliers(q?: string, opts?: CatalogListOpts) {
  const { data, error } = await api.GET("/api/suppliers", {
    params: {
      query: {
        q: q || undefined,
        active_only: opts?.activeOnly ?? false,
        limit: opts?.limit ?? 50,
        offset: opts?.offset ?? 0,
      },
    },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar fornecedores"));
  return data ?? [];
}

export async function fetchSupplierList(query: {
  q?: string;
  activeOnly?: boolean;
  missingTaxId?: boolean;
  sort?: string;
  limit?: number;
  offset?: number;
}): Promise<SupplierList> {
  const { data, error } = await api.GET("/api/catalog/supplier-list", {
    params: {
      query: {
        q: query.q || undefined,
        active_only: query.activeOnly ?? false,
        missing_tax_id: query.missingTaxId ?? false,
        sort: query.sort || undefined,
        limit: query.limit ?? 50,
        offset: query.offset ?? 0,
      },
    },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar fornecedores"));
  return data ?? { items: [], total: 0, limit: query.limit ?? 50, offset: query.offset ?? 0 };
}

export async function getSupplier(id: number) {
  const { data, error } = await api.GET("/api/suppliers/{supplier_id}", {
    params: { path: { supplier_id: id } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar fornecedor"));
  return data!;
}

export async function createSupplier(body: {
  name: string;
  code?: string;
  country_code?: string;
  is_active?: boolean;
  tax_id?: string | null;
}) {
  const { data, error } = await api.POST("/api/suppliers", {
    body: { is_active: true, ...body },
  });
  if (error) throw new Error(errMsg(error, "Erro ao criar fornecedor"));
  return data!;
}

export async function patchSupplier(id: number, body: SupplierPatch) {
  const { data, error } = await api.PATCH("/api/suppliers/{supplier_id}", {
    params: { path: { supplier_id: id } },
    body,
  });
  if (error) throw new Error(errMsg(error, "Erro ao atualizar fornecedor"));
  return data!;
}

export async function listProducts(q?: string, opts?: CatalogListOpts) {
  const { data, error } = await api.GET("/api/products", {
    params: {
      query: {
        q: q || undefined,
        active_only: opts?.activeOnly ?? false,
        limit: opts?.limit ?? 50,
        offset: opts?.offset ?? 0,
      },
    },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar produtos"));
  return data ?? [];
}

export async function fetchProductList(query: {
  q?: string;
  activeOnly?: boolean;
  isActive?: boolean | null;
  incomplete?: boolean;
  missingNcm?: boolean;
  missingImage?: boolean;
  needsReview?: boolean;
  needsClassificationReview?: boolean;
  shortGeneric?: boolean;
  qualityIncomplete?: boolean;
  category?: string;
  subcategory?: string;
  productType?: string;
  sport?: string;
  collectionYear?: string;
  color?: string;
  size?: string;
  origin?: string;
  unit?: string;
  ean?: string;
  supplierSku?: string;
  model?: string;
  garmentKind?: string;
  gender?: string;
  sourceKind?: string;
  sort?: string;
  limit?: number;
  offset?: number;
}): Promise<ProductList> {
  const { data, error } = await api.GET("/api/catalog/product-list", {
    params: {
      query: {
        q: query.q || undefined,
        active_only: query.activeOnly ?? false,
        is_active: query.isActive ?? undefined,
        incomplete: query.incomplete ?? false,
        missing_ncm: query.missingNcm ?? false,
        missing_image: query.missingImage ?? false,
        needs_review: query.needsReview ?? false,
        needs_classification_review: query.needsClassificationReview ?? false,
        short_generic: query.shortGeneric ?? false,
        quality_incomplete: query.qualityIncomplete ?? false,
        category: query.category || undefined,
        subcategory: query.subcategory || undefined,
        product_type: query.productType || undefined,
        sport: query.sport || undefined,
        collection_year: query.collectionYear || undefined,
        color: query.color || undefined,
        size: query.size || undefined,
        origin: query.origin || undefined,
        unit: query.unit || undefined,
        ean: query.ean || undefined,
        supplier_sku: query.supplierSku || undefined,
        model: query.model || undefined,
        garment_kind: query.garmentKind || undefined,
        gender: query.gender || undefined,
        source_kind: query.sourceKind || undefined,
        sort: query.sort || undefined,
        limit: query.limit ?? 50,
        offset: query.offset ?? 0,
      },
    },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar produtos"));
  return (
    data ?? {
      items: [],
      total: 0,
      limit: query.limit ?? 50,
      offset: query.offset ?? 0,
      summary: {
        total: 0,
        incomplete: 0,
        missing_ncm: 0,
        needs_review: 0,
        needs_product_review: 0,
        needs_classification_review: 0,
        short_generic: 0,
        missing_image: 0,
        quality_incomplete: 0,
      },
      facets: {},
    }
  );
}

export async function getProduct(id: number) {
  const { data, error } = await api.GET("/api/products/{product_id}", {
    params: { path: { product_id: id } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao carregar produto"));
  return data!;
}

export async function createProduct(body: { sku: string; description: string; is_active?: boolean }) {
  const { data, error } = await api.POST("/api/products", {
    body: { is_active: true, ...body },
  });
  if (error) throw new Error(errMsg(error, "Erro ao criar produto"));
  return data!;
}

export async function patchProduct(id: number, body: ProductPatch) {
  const { data, error } = await api.PATCH("/api/products/{product_id}", {
    params: { path: { product_id: id } },
    body,
  });
  if (error) throw new Error(errMsg(error, "Erro ao atualizar produto"));
  return data!;
}

export async function fetchProductAttributeValues(
  field:
    | "size"
    | "color"
    | "country_of_origin"
    | "unit"
    | "subcategory"
    | "ean"
    | "supplier_sku"
    | "sport"
    | "model"
    | "collection_year"
    | "line"
    | "garment_kind"
    | "gender",
) {
  const { data, error } = await api.GET("/api/catalog/product-attribute-values", {
    params: { query: { field } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar valores"));
  return data?.values ?? [];
}

export async function fetchTaxonomy(): Promise<Taxonomy> {
  const { data, error } = await api.GET("/api/catalog/taxonomy", {});
  if (error) throw new Error(errMsg(error, "Erro ao carregar classificação"));
  return data ?? { categories: [], product_types: [] };
}
