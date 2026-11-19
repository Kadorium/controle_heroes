import type { User } from "../features/auth/types";

export type NavigationSection = {
  id: string;
  label: string;
  to: string;
  permission: string;
  paths?: string[];
};
export type NavigationArea = {
  id: string;
  label: string;
  icon: string;
  secondary?: boolean;
  sections: NavigationSection[];
};

// Presentation only: section permissions remain owned by their pages and APIs.
// Order is stable. The first permitted section is the area's entry point.
export const NAVIGATION: NavigationArea[] = [
  { id: "overview", label: "Visão geral", icon: "home", sections: [
    { id: "dashboard", label: "Visão geral", to: "/dashboard", permission: "reporting:read" },
  ] },
  { id: "products", label: "Produtos", icon: "product", sections: [
    { id: "stock", label: "Estoque atual", to: "/inventory/positions", permission: "inventory:read", paths: ["/inventory/positions", "/inventory/sku"] },
    { id: "catalog", label: "Catálogo e preços", to: "/catalog/products", permission: "catalog:read", paths: ["/catalog/products", "/catalog/prices"] },
    { id: "history", label: "Histórico de estoque", to: "/inventory/movements", permission: "inventory:read" },
  ] },
  { id: "purchases", label: "Compras", icon: "purchase", sections: [
    { id: "orders", label: "Pedidos", to: "/orders", permission: "orders:read" },
    { id: "invoices", label: "Faturas", to: "/invoices", permission: "billing:read" },
    { id: "suppliers", label: "Fornecedores", to: "/catalog/suppliers", permission: "catalog:read" },
  ] },
  { id: "imports", label: "Importações", icon: "shipment", sections: [
    { id: "operations", label: "Operações", to: "/customs", permission: "customs:read" },
    { id: "receiving", label: "Mercadorias a receber", to: "/inventory/receiving", permission: "inventory:read" },
    { id: "shipments", label: "Embarques", to: "/shipments", permission: "logistics:read" },
    { id: "costing", label: "Custo desembarcado", to: "/costing", permission: "costing:read" },
    { id: "providers", label: "Prestadores logísticos", to: "/logistics-providers", permission: "logistics:read" },
  ] },
  { id: "finance", label: "Financeiro", icon: "money", sections: [
    { id: "payables", label: "Contas a pagar", to: "/payables", permission: "billing:read" },
    { id: "payments", label: "Pagamentos realizados", to: "/payments", permission: "treasury:read" },
    // Existing FX URL remains available when the user cannot enter the AP queue.
    { id: "fx", label: "Câmbio por obrigação", to: "/payables?purpose=fx", permission: "treasury:fx_read", paths: ["/payables"] },
  ] },
  { id: "documents", label: "Conferir documentos", icon: "document", secondary: true, sections: [
    { id: "documents", label: "Conferir documentos", to: "/ingestion", permission: "ingestion:read" },
  ] },
  { id: "access", label: "Usuários e acessos", icon: "users", secondary: true, sections: [
    { id: "users", label: "Usuários e acessos", to: "/admin/users", permission: "users:read" },
  ] },
];

export function canNavigate(user: User, permission: string): boolean {
  return user.role === "admin" || user.permissions.includes(permission);
}

export function visibleNavigation(user: User): NavigationArea[] {
  return NAVIGATION.map(area => ({ ...area, sections: area.sections.filter(section =>
    canNavigate(user, section.permission) && (section.id !== "fx" || !canNavigate(user, "billing:read")),
  ) })).filter(area => area.sections.length > 0);
}

export function sectionMatches(section: NavigationSection, pathname: string): boolean {
  return (section.paths ?? [section.to.split("?")[0]]).some(path => pathname === path || pathname.startsWith(path + "/"));
}

export function activeNavigation(areas: NavigationArea[], pathname: string) {
  const area = areas.find(item => item.sections.some(section => sectionMatches(section, pathname)));
  return { area, section: area?.sections.find(section => sectionMatches(section, pathname)) };
}
