import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type Supplier = components["schemas"]["SupplierResponse"];
export type Product = components["schemas"]["ProductResponse"];
export type ProductList = components["schemas"]["ProductListResponse"];
export type SupplierList = components["schemas"]["SupplierListResponse"];
export type ProductPatch = components["schemas"]["ProductPatch"];
export type SupplierPatch = components["schemas"]["SupplierPatch"];

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
  incomplete?: boolean;
  missingNcm?: boolean;
  size?: string;
  color?: string;
  sort?: string;
  limit?: number;
  offset?: number;
}): Promise<ProductList> {
  const { data, error } = await api.GET("/api/catalog/product-list", {
    params: {
      query: {
        q: query.q || undefined,
        active_only: query.activeOnly ?? false,
        incomplete: query.incomplete ?? false,
        missing_ncm: query.missingNcm ?? false,
        size: query.size || undefined,
        color: query.color || undefined,
        sort: query.sort || undefined,
        limit: query.limit ?? 50,
        offset: query.offset ?? 0,
      },
    },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar produtos"));
  return data ?? { items: [], total: 0, limit: query.limit ?? 50, offset: query.offset ?? 0 };
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

export async function fetchProductAttributeValues(field: "size" | "color") {
  const { data, error } = await api.GET("/api/catalog/product-attribute-values", {
    params: { query: { field } },
  });
  if (error) throw new Error(errMsg(error, "Erro ao listar valores"));
  return data?.values ?? [];
}
