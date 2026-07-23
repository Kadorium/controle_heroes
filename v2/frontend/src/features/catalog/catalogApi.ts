import { api } from "../../api/generated/client";
import type { components } from "../../api/generated/schema";

export type Supplier = components["schemas"]["SupplierResponse"];
export type Product = components["schemas"]["ProductResponse"];

export async function listSuppliers(q?: string) {
  const { data, error } = await api.GET("/api/suppliers", { params: { query: { q, limit: 50 } } });
  if (error) throw new Error((error as { message?: string }).message || "Erro ao listar fornecedores");
  return data ?? [];
}

export async function createSupplier(body: {
  name: string;
  code?: string;
  country_code?: string;
  is_active?: boolean;
}) {
  const { data, error } = await api.POST("/api/suppliers", {
    body: { is_active: true, ...body },
  });
  if (error) throw new Error((error as { message?: string }).message || "Erro ao criar fornecedor");
  return data!;
}

export async function listProducts(q?: string) {
  const { data, error } = await api.GET("/api/products", { params: { query: { q, limit: 50 } } });
  if (error) throw new Error((error as { message?: string }).message || "Erro ao listar produtos");
  return data ?? [];
}

export async function createProduct(body: { sku: string; description: string; is_active?: boolean }) {
  const { data, error } = await api.POST("/api/products", {
    body: { is_active: true, ...body },
  });
  if (error) throw new Error((error as { message?: string }).message || "Erro ao criar produto");
  return data!;
}
