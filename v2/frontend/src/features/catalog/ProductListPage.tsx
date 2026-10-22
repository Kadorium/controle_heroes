import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { User } from "../auth/types";
import {
  fetchProductAttributeValues,
  fetchProductList,
  fetchSupplierList,
  type Product,
  type ProductList,
  type ProductListSummary,
} from "./catalogApi";
import { classificationLine, productIdentity } from "./productIdentity";
import { useListReturn } from "../../navigation/useListReturn";
import { saveReturnState } from "../../navigation/returnState";
import {
  EmptyState,
  ErrorState,
  FilterBar,
  FilterChip,
  LoadingState,
  OperationalTable,
  PageHeader,
  PaginationSummary,
  TextInput,
  type OperationalColumnDef,
} from "../../ui";

type Props = { user: User };

const PAGE = 50;
const DEBOUNCE_MS = 280;
const CATEGORIES = [
  { slug: "", label: "Todos" },
  { slug: "raquetes", label: "Raquetes" },
  { slug: "acessorios", label: "Acessórios" },
  { slug: "vestuario", label: "Vestuário" },
] as const;

function canWrite(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("catalog:write");
}

function canReadCatalog(user: User) {
  return user.role === "admin" || (user.permissions ?? []).includes("catalog:read");
}

function csvToggle(current: string, token: string): string {
  const parts = current.split(",").filter(Boolean);
  const next = parts.includes(token) ? parts.filter((v) => v !== token) : [...parts, token];
  return next.join(",");
}

function sortLabel(sort: string): string {
  if (sort === "sku") return "SKU";
  if (sort === "quality") return "Qualidade";
  return "Nome";
}

function emptySummary(): ProductListSummary {
  return {
    total: 0,
    incomplete: 0,
    missing_ncm: 0,
    needs_review: 0,
    needs_product_review: 0,
    needs_classification_review: 0,
    short_generic: 0,
    missing_image: 0,
    quality_incomplete: 0,
  };
}

export function ProductListPage({ user }: Props) {
  const location = useLocation();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") ?? "";
  const active = params.get("active") ?? "";
  const incomplete = params.get("incomplete") === "1";
  const qualityIncomplete = params.get("quality") === "1" || incomplete;
  const missingNcm = params.get("missing_ncm") === "1";
  const missingImage = params.get("missing_image") === "1";
  const needsReview = params.get("review") === "1";
  const needsClassificationReview = params.get("taxonomy_review") === "1";
  const shortGeneric = params.get("short_generic") === "1";
  const category = params.get("category") ?? "";
  const size = params.get("size") ?? "";
  const color = params.get("color") ?? "";
  const origin = params.get("origin") ?? "";
  const sport = params.get("sport") ?? "";
  const collectionYear = params.get("year") ?? "";
  const model = params.get("model") ?? "";
  const garmentKind = params.get("piece") ?? "";
  const gender = params.get("gender") ?? "";
  const unit = params.get("unit") ?? "";
  const ean = params.get("ean") ?? "";
  const supplierSku = params.get("supplier_sku") ?? "";
  const sourceKind = params.get("source") ?? "";
  const productType = params.get("type") ?? "";
  const sort = params.get("sort") || "commercial_name";
  const offset = Number(params.get("offset") || "0") || 0;
  const [rows, setRows] = useState<Product[] | null>(null);
  const [total, setTotal] = useState(0);
  const [summary, setSummary] = useState<ProductListSummary>(emptySummary());
  const [facets, setFacets] = useState<ProductList["facets"]>({});
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(params.get("row") || null);
  const [picked, setPicked] = useState<number[]>([]);
  const [draftQ, setDraftQ] = useState(q);
  const [menuOpen, setMenuOpen] = useState(false);
  const [sortOpen, setSortOpen] = useState(false);
  const [principalHref, setPrincipalHref] = useState("/catalog/suppliers");
  const [sizes, setSizes] = useState<string[]>([]);
  const [origins, setOrigins] = useState<string[]>([]);

  useListReturn("/catalog/products", selectedId);

  useEffect(() => {
    setDraftQ(q);
  }, [q]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      if (draftQ.trim() === q) return;
      const next = new URLSearchParams(params);
      if (!draftQ.trim()) next.delete("q");
      else next.set("q", draftQ.trim());
      next.delete("offset");
      setParams(next);
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [draftQ]); // eslint-disable-line react-hooks/exhaustive-deps -- debounce only on draft

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    void (async () => {
      try {
        const data = await fetchProductList({
          q: q || undefined,
          isActive: active === "1" ? true : active === "0" ? false : null,
          qualityIncomplete,
          missingNcm,
          missingImage,
          needsReview,
          needsClassificationReview,
          shortGeneric,
          category: category || undefined,
          size: size || undefined,
          color: color || undefined,
          origin: origin || undefined,
          sport: sport || undefined,
          collectionYear: collectionYear || undefined,
          model: model || undefined,
          garmentKind: garmentKind || undefined,
          gender: gender || undefined,
          unit: unit || undefined,
          ean: ean || undefined,
          supplierSku: supplierSku || undefined,
          sourceKind: sourceKind || undefined,
          productType: productType || undefined,
          sort,
          limit: PAGE,
          offset,
        });
        if (!cancelled) {
          setRows(data.items);
          setTotal(data.total);
          setSummary(data.summary ?? emptySummary());
          setFacets(data.facets ?? {});
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Erro");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [
    q,
    active,
    qualityIncomplete,
    missingNcm,
    missingImage,
    needsReview,
    needsClassificationReview,
    shortGeneric,
    category,
    size,
    color,
    origin,
    sport,
    collectionYear,
    model,
    garmentKind,
    gender,
    unit,
    ean,
    supplierSku,
    sourceKind,
    productType,
    sort,
    offset,
  ]);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([
      fetchProductAttributeValues("size").catch(() => [] as string[]),
      fetchProductAttributeValues("country_of_origin").catch(() => [] as string[]),
    ]).then(([s, o]) => {
      if (!cancelled) {
        setSizes(s);
        setOrigins(o);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  function setParam(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (!value) next.delete(key);
    else next.set(key, value);
    next.delete("offset");
    setParams(next);
  }

  const rememberRow = useCallback(
    (id: number) => {
      setSelectedId(String(id));
      saveReturnState("/catalog/products", {
        search: location.search,
        scrollY: window.scrollY,
        selectedId: String(id),
      });
    },
    [location.search],
  );

  const returnTo = `${location.pathname}${location.search}`;
  const columns = useMemo(
    (): OperationalColumnDef<Product>[] => [
      {
        id: "select",
        header: "",
        visibility: "always",
        priority: 0,
        minWidth: "2.5rem",
        cell: (row) => (
          <input
            type="checkbox"
            aria-label={`Selecionar ${row.commercial_name || row.description}`}
            checked={picked.includes(row.id)}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => {
              setPicked((prev) => {
                if (e.target.checked) return prev.includes(row.id) || prev.length >= 3 ? prev : [...prev, row.id];
                return prev.filter((id) => id !== row.id);
              });
            }}
          />
        ),
      },
      {
        id: "product",
        header: "Produto",
        visibility: "always",
        priority: 0,
        minWidth: "22rem",
        cell: (row) => {
          const idn = productIdentity(row);
          const traits = row.quality?.traits ?? [];
          return (
            <div className="product-rich-cell">
              <div className="product-thumb" aria-hidden="true">
                <span>Sem foto</span>
              </div>
              <div>
                <div className="cell-primary">{idn.title}</div>
                <div className="cell-secondary">{classificationLine(row) || idn.sub}</div>
                {traits.length ? <div className="cell-traits">{traits.join(" · ")}</div> : null}
              </div>
            </div>
          );
        },
      },
      {
        id: "quality",
        header: "Qualidade",
        visibility: "always",
        priority: 0,
        minWidth: "9rem",
        cell: (row) => {
          const pending = row.quality?.pending_count ?? 0;
          if (row.needs_classification_review) {
            return <span className="status-badge status-warn">Revisar classificação</span>;
          }
          if (row.needs_review) {
            return <span className="status-badge status-warn">Precisa revisar</span>;
          }
          if (pending > 0) {
            return <span className="status-badge status-info">{pending} pendência{pending === 1 ? "" : "s"}</span>;
          }
          return <span className="status-badge status-ok">Essencial completo</span>;
        },
      },
      {
        id: "status",
        header: "Situação",
        visibility: "always",
        priority: 0,
        minWidth: "6rem",
        cell: (row) =>
          row.is_active ? (
            <span className="status-badge status-ok">Ativo</span>
          ) : (
            <span className="status-badge status-neutral">Inativo</span>
          ),
      },
      {
        id: "sku",
        header: "SKU",
        visibility: "standard",
        priority: 2,
        minWidth: "8rem",
        cell: (row) => <span className="cell-secondary">{row.sku}</span>,
      },
    ],
    [picked],
  );

  const hasQuery = Boolean(
    q ||
      active ||
      qualityIncomplete ||
      missingNcm ||
      missingImage ||
      needsReview ||
      needsClassificationReview ||
      shortGeneric ||
      category ||
      size ||
      color ||
      origin ||
      sport ||
      collectionYear ||
      model ||
      garmentKind ||
      gender ||
      unit ||
      ean ||
      supplierSku ||
      sourceKind ||
      productType,
  );
  const activeFilters = [
    q ? { id: "q", label: `Busca: ${q}`, onRemove: () => setParam("q", "") } : null,
    category ? { id: "cat", label: CATEGORIES.find((c) => c.slug === category)?.label || category, onRemove: () => setParam("category", "") } : null,
    active === "1" ? { id: "active", label: "Ativos", onRemove: () => setParam("active", "") } : null,
    active === "0" ? { id: "inactive", label: "Inativos", onRemove: () => setParam("active", "") } : null,
    needsReview ? { id: "review", label: "Precisa revisar", onRemove: () => setParam("review", "") } : null,
    needsClassificationReview
      ? { id: "tax-review", label: "Revisar classificação", onRemove: () => setParam("taxonomy_review", "") }
      : null,
    shortGeneric
      ? { id: "short", label: "Descrição a enriquecer", onRemove: () => setParam("short_generic", "") }
      : null,
    qualityIncomplete ? { id: "quality", label: "Cadastro incompleto", onRemove: () => { setParam("quality", ""); setParam("incomplete", ""); } } : null,
    missingImage ? { id: "img", label: "Sem imagem", onRemove: () => setParam("missing_image", "") } : null,
    missingNcm ? { id: "ncm", label: "Sem NCM", onRemove: () => setParam("missing_ncm", "") } : null,
    sourceKind === "heroes_csv"
      ? { id: "src", label: "Catálogo histórico", onRemove: () => setParam("source", "") }
      : null,
    productType ? { id: "type", label: `Tipo: ${productType}`, onRemove: () => setParam("type", "") } : null,
    ean ? { id: "ean", label: `EAN: ${ean}`, onRemove: () => setParam("ean", "") } : null,
    supplierSku ? { id: "sup", label: `Fornecedor: ${supplierSku}`, onRemove: () => setParam("supplier_sku", "") } : null,
    ...size.split(",").filter(Boolean).map((token) => ({ id: `size-${token}`, label: `Tamanho: ${token}`, onRemove: () => setParam("size", csvToggle(size, token)) })),
    ...color.split(",").filter(Boolean).map((token) => ({ id: `color-${token}`, label: `Cor: ${token}`, onRemove: () => setParam("color", csvToggle(color, token)) })),
    ...origin.split(",").filter(Boolean).map((token) => ({ id: `origin-${token}`, label: `Origem: ${token}`, onRemove: () => setParam("origin", csvToggle(origin, token)) })),
  ].filter(Boolean) as { id: string; label: string; onRemove: () => void }[];

  async function openOverflow() {
    setSortOpen(false);
    setMenuOpen((v) => !v);
    try {
      const data = await fetchSupplierList({ q: "Hero", activeOnly: true, limit: 1 });
      const row = data.items[0] ?? (await fetchSupplierList({ activeOnly: true, limit: 1 })).items[0];
      if (row) setPrincipalHref(`/catalog/suppliers/${row.id}`);
    } catch {
      setPrincipalHref("/catalog/suppliers");
    }
  }

  if (error) return <ErrorState message={error} />;
  if (rows === null) return <LoadingState message="Carregando produtos…" />;

  const emptyCatalog = rows.length === 0 && !hasQuery && offset === 0;
  const noResults = rows.length === 0 && hasQuery;
  const pages = Math.max(1, Math.ceil(total / PAGE));
  const pageIndex = Math.floor(offset / PAGE);
  const facetSport = facets?.sport ?? [];
  const facetYear = facets?.collection_year ?? [];
  const facetModel = facets?.model ?? [];
  const facetPiece = facets?.garment_kind ?? [];
  const facetGender = facets?.gender ?? [];
  const facetColor = facets?.color ?? [];
  const facetUnit = facets?.unit ?? [];
  const facetType = facets?.product_type ?? [];

  return (
    <section className="panel dense" data-testid="product-list-page">
      <PageHeader
        title="Produtos"
        subtitle="Catálogo comercial · busca por nome, características, SKU ou EAN"
        actions={
          <div className="header-actions">
            {picked.length >= 2 ? (
              <Link
                className="ui-button ui-button--secondary"
                to={`/catalog/products/compare?ids=${picked.join(",")}`}
                data-testid="products-compare"
              >
                Comparar {picked.length}
              </Link>
            ) : null}
            {canReadCatalog(user) ? (
              <div className="overflow-anchor">
                <button
                  type="button"
                  className="ui-button ui-button--secondary"
                  data-testid="catalog-overflow"
                  aria-expanded={menuOpen}
                  onClick={() => void openOverflow()}
                >
                  ⋯
                </button>
                {menuOpen ? (
                  <div className="overflow-menu" role="menu">
                    <Link to={principalHref} role="menuitem" onClick={() => setMenuOpen(false)}>
                      Fornecedor principal
                    </Link>
                    <Link to="/catalog/suppliers" role="menuitem" onClick={() => setMenuOpen(false)}>
                      Gerenciar fornecedores
                    </Link>
                  </div>
                ) : null}
              </div>
            ) : null}
            {canWrite(user) ? (
              <Link className="ui-button" to="/catalog/products/new" data-testid="products-new-cta">
                + Novo produto
              </Link>
            ) : null}
          </div>
        }
      />
      <div className="kpi-inline" data-testid="kpi-inline">
        <button type="button" className={!hasQuery ? "is-on" : undefined} onClick={() => setParams(new URLSearchParams())}>
          {summary.total} produtos
        </button>
        <span className="kpi-dot">·</span>
        <button type="button" className={needsReview ? "is-on" : undefined} onClick={() => setParam("review", "1")}>
          {summary.needs_review} precisam revisão
        </button>
        <span className="kpi-dot">·</span>
        <button
          type="button"
          className={needsClassificationReview ? "is-on" : undefined}
          onClick={() => setParam("taxonomy_review", "1")}
        >
          {summary.needs_classification_review} classificação
        </button>
        <span className="kpi-dot">·</span>
        <button
          type="button"
          className={shortGeneric ? "is-on" : undefined}
          onClick={() => setParam("short_generic", "1")}
        >
          {summary.short_generic} descrição a enriquecer
        </button>
        <span className="kpi-dot">·</span>
        <button
          type="button"
          className={qualityIncomplete ? "is-on" : undefined}
          onClick={() => setParam("quality", "1")}
        >
          {summary.quality_incomplete} incompletos
        </button>
      </div>
      <div className="queue-shell">
        <FilterBar
          moreAlways
          primary={
            <div className="stack-row" style={{ flexWrap: "wrap", gap: "0.5rem", alignItems: "center", flex: 1 }}>
              <label className="search-wrap">
                <span className="sr-only">Buscar produtos</span>
                <TextInput
                  data-testid="products-search"
                  value={draftQ}
                  onChange={(e) => setDraftQ(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Escape") {
                      setDraftQ("");
                      setParam("q", "");
                    }
                  }}
                  placeholder="Buscar por nome, esporte, modelo, SKU ou EAN"
                  aria-label="Buscar produtos"
                />
              </label>
              {CATEGORIES.map((item) => (
                <FilterChip
                  key={item.slug || "all"}
                  pressed={category === item.slug}
                  data-testid={item.slug ? `products-filter-${item.slug}` : "products-filter-all"}
                  onClick={() => setParam("category", category === item.slug ? "" : item.slug)}
                >
                  {item.label}
                </FilterChip>
              ))}
              <FilterChip pressed={active === "1"} data-testid="products-filter-active" onClick={() => setParam("active", active === "1" ? "" : "1")}>
                Ativos
              </FilterChip>
              <FilterChip pressed={active === "0"} data-testid="products-filter-inactive" onClick={() => setParam("active", active === "0" ? "" : "0")}>
                Inativos
              </FilterChip>
              <FilterChip pressed={needsReview} data-testid="products-filter-review" onClick={() => setParam("review", needsReview ? "" : "1")}>
                Precisa revisar
              </FilterChip>
              <FilterChip
                pressed={needsClassificationReview}
                data-testid="products-filter-taxonomy-review"
                onClick={() => setParam("taxonomy_review", needsClassificationReview ? "" : "1")}
              >
                Revisar classificação
              </FilterChip>
              <FilterChip
                pressed={shortGeneric}
                data-testid="products-filter-short-generic"
                onClick={() => setParam("short_generic", shortGeneric ? "" : "1")}
              >
                Descrição a enriquecer
              </FilterChip>
              <FilterChip
                pressed={qualityIncomplete}
                data-testid="products-filter-incomplete"
                onClick={() => setParam("quality", qualityIncomplete ? "" : "1")}
              >
                Cadastro incompleto
              </FilterChip>
              <FilterChip pressed={missingImage} data-testid="products-filter-no-image" onClick={() => setParam("missing_image", missingImage ? "" : "1")}>
                Sem imagem
              </FilterChip>
            </div>
          }
          secondary={
            <div className="facet-popover">
              {category === "raquetes" && facetSport.length ? (
                <div className="facet-compact">
                  <div className="facet-label">Esporte</div>
                  <div className="facet-pills">
                    {facetSport.map((item) => (
                      <FilterChip key={item.value} pressed={sport === item.value} onClick={() => setParam("sport", sport === item.value ? "" : item.value)}>
                        {item.value}
                      </FilterChip>
                    ))}
                  </div>
                </div>
              ) : null}
              {category === "raquetes" && facetYear.length ? (
                <div className="facet-compact">
                  <div className="facet-label">Coleção</div>
                  <div className="facet-pills">
                    {facetYear.map((item) => (
                      <FilterChip key={item.value} pressed={collectionYear === item.value} onClick={() => setParam("year", collectionYear === item.value ? "" : item.value)}>
                        {item.value}
                      </FilterChip>
                    ))}
                  </div>
                </div>
              ) : null}
              {category === "raquetes" && facetModel.length ? (
                <div className="facet-compact">
                  <div className="facet-label">Modelo</div>
                  <div className="facet-pills">
                    {facetModel.map((item) => (
                      <FilterChip key={item.value} pressed={model === item.value} onClick={() => setParam("model", model === item.value ? "" : item.value)}>
                        {item.value}
                      </FilterChip>
                    ))}
                  </div>
                </div>
              ) : null}
              {category === "vestuario" && facetPiece.length ? (
                <div className="facet-compact">
                  <div className="facet-label">Peça</div>
                  <div className="facet-pills">
                    {facetPiece.map((item) => (
                      <FilterChip key={item.value} pressed={garmentKind === item.value} onClick={() => setParam("piece", garmentKind === item.value ? "" : item.value)}>
                        {item.value}
                      </FilterChip>
                    ))}
                  </div>
                </div>
              ) : null}
              {category === "vestuario" && facetGender.length ? (
                <div className="facet-compact">
                  <div className="facet-label">Gênero</div>
                  <div className="facet-pills">
                    {facetGender.map((item) => (
                      <FilterChip key={item.value} pressed={gender === item.value} onClick={() => setParam("gender", gender === item.value ? "" : item.value)}>
                        {item.value}
                      </FilterChip>
                    ))}
                  </div>
                </div>
              ) : null}
              {facetColor.length ? (
                <div className="facet-compact">
                  <div className="facet-label">Cor</div>
                  <div className="facet-pills">
                    {facetColor.map((item) => (
                      <FilterChip key={item.value} pressed={color.split(",").includes(item.value)} onClick={() => setParam("color", csvToggle(color, item.value))}>
                        {item.value}
                      </FilterChip>
                    ))}
                  </div>
                </div>
              ) : null}
              {facetType.length ? (
                <div className="facet-compact">
                  <div className="facet-label">Tipo</div>
                  <div className="facet-pills">
                    {facetType.map((item) => (
                      <FilterChip key={item.value} pressed={productType === item.value} onClick={() => setParam("type", productType === item.value ? "" : item.value)}>
                        {item.label || item.value}
                      </FilterChip>
                    ))}
                  </div>
                </div>
              ) : null}
              {facetUnit.length ? (
                <div className="facet-compact">
                  <div className="facet-label">Unidade</div>
                  <div className="facet-pills">
                    {facetUnit.map((item) => (
                      <FilterChip key={item.value} pressed={unit === item.value} onClick={() => setParam("unit", unit === item.value ? "" : item.value)}>
                        {item.value}
                      </FilterChip>
                    ))}
                  </div>
                </div>
              ) : null}
              {sizes.length ? (
                <div className="facet-compact">
                  <div className="facet-label">Tamanho</div>
                  <div className="facet-pills">
                    {sizes.map((value) => (
                      <FilterChip key={value} pressed={size.split(",").includes(value)} onClick={() => setParam("size", csvToggle(size, value))}>
                        {value}
                      </FilterChip>
                    ))}
                  </div>
                </div>
              ) : null}
              {origins.length ? (
                <div className="facet-compact">
                  <div className="facet-label">Origem</div>
                  <div className="facet-pills">
                    {origins.map((value) => (
                      <FilterChip key={value} pressed={origin.split(",").includes(value)} onClick={() => setParam("origin", csvToggle(origin, value))}>
                        {value}
                      </FilterChip>
                    ))}
                  </div>
                </div>
              ) : null}
              <div className="facet-compact">
                <div className="facet-label">Fiscal</div>
                <FilterChip pressed={missingNcm} data-testid="products-filter-ncm" onClick={() => setParam("missing_ncm", missingNcm ? "" : "1")}>
                  Sem NCM
                </FilterChip>
              </div>
              <div className="facet-compact">
                <div className="facet-label">Origem do lote</div>
                <FilterChip
                  pressed={sourceKind === "heroes_csv"}
                  data-testid="products-filter-historical"
                  onClick={() => setParam("source", sourceKind === "heroes_csv" ? "" : "heroes_csv")}
                >
                  Catálogo histórico
                </FilterChip>
              </div>
              <div className="facet-compact">
                <div className="facet-label">EAN / código fornecedor</div>
                <TextInput
                  data-testid="products-filter-ean"
                  placeholder="EAN"
                  value={ean}
                  onChange={(e) => setParam("ean", e.target.value.trim())}
                />
                <TextInput
                  data-testid="products-filter-supplier-sku"
                  placeholder="Código do fornecedor"
                  value={supplierSku}
                  onChange={(e) => setParam("supplier_sku", e.target.value.trim())}
                />
              </div>
            </div>
          }
          activeFilters={activeFilters}
          onClearAll={hasQuery ? () => setParams(new URLSearchParams()) : undefined}
        />
      </div>
      {emptyCatalog ? (
        <EmptyState title="Catálogo vazio" message="Cadastre o primeiro produto para usá-lo nos pedidos." />
      ) : noResults ? (
        <EmptyState title="Nenhum resultado" message="Nenhum produto corresponde à busca ou aos filtros. Ajuste a consulta ou limpe os filtros." />
      ) : (
        <>
          <div className="list-meta">
            <PaginationSummary offset={offset} limit={PAGE} total={total} loadedCount={rows.length} />
            <div className="sort-anchor">
              <button
                type="button"
                className="sort-btn"
                data-testid="products-sort"
                aria-expanded={sortOpen}
                onClick={() => {
                  setMenuOpen(false);
                  setSortOpen((v) => !v);
                }}
              >
                Ordenar: <strong>{sortLabel(sort)}</strong>
              </button>
              {sortOpen ? (
                <div className="sort-menu" role="menu">
                  {(["commercial_name", "sku", "quality"] as const).map((key) => (
                    <button
                      key={key}
                      type="button"
                      role="menuitemradio"
                      aria-checked={sort === key}
                      onClick={() => {
                        setSortOpen(false);
                        setParam("sort", key === "commercial_name" ? "" : key);
                      }}
                    >
                      {sortLabel(key)}
                    </button>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
          <OperationalTable
            density="standard"
            data-testid="products-table"
            columns={columns}
            rows={rows}
            getRowId={(row) => String(row.id)}
            selectedId={selectedId}
            onRowClick={(row) => {
              rememberRow(row.id);
              navigate(`/catalog/products/${row.id}`, { state: { returnTo } });
            }}
          />
          <div className="page-btns">
            <button
              type="button"
              className="ui-button ui-button--secondary"
              disabled={offset === 0}
              onClick={() => {
                const next = new URLSearchParams(params);
                const off = Math.max(0, offset - PAGE);
                if (off <= 0) next.delete("offset");
                else next.set("offset", String(off));
                setParams(next);
              }}
            >
              Anterior
            </button>
            <span>
              página {pageIndex + 1} de {pages}
            </span>
            {offset + PAGE < total ? (
              <button
                type="button"
                className="ui-button ui-button--secondary"
                data-testid="products-next-page"
                onClick={() => {
                  const next = new URLSearchParams(params);
                  next.set("offset", String(offset + PAGE));
                  setParams(next);
                }}
              >
                Próxima
              </button>
            ) : (
              <button type="button" className="ui-button ui-button--secondary" data-testid="products-next-page" disabled>
                Próxima
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}
