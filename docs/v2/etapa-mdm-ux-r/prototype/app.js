const PAGE = 20;
const DEBOUNCE_MS = 280;
const SESSION_KEY = "mdm-ux-r-proto-v1";

const ICONS = {
  products:
    "M4.2 3.1h11.6v3.4H4.2V3.1zm0 4.6h11.6v9.2H4.2V7.7zm2.2 2.1h7.2v1.4H6.4V9.8zm0 2.8h5.1v1.4H6.4v-1.4z",
  orders:
    "M6.7 1.35h6.6c.7 0 1.25.55 1.25 1.25v2.15H5.45V2.6c0-.7.55-1.25 1.25-1.25zM3.6 4.75h12.8c.7 0 1.25.55 1.25 1.25v10.2c0 .7-.55 1.25-1.25 1.25H3.6c-.7 0-1.25-.55-1.25-1.25V6c0-.7.55-1.25 1.25-1.25z",
  invoices:
    "M5.15 1.7h9.7a1.1 1.1 0 0 1 1.1 1.1v14.4a1.1 1.1 0 0 1-1.1 1.1H5.15a1.1 1.1 0 0 1-1.1-1.1V2.8a1.1 1.1 0 0 1 1.1-1.1z",
  ingestion:
    "M9 1.55h2v5.5h2.7L10 12 6.3 7.05H9V1.55zM2.6 12.05h14.8v1.55H15.6L14.05 18H5.95L4.4 13.6H2.6v-1.55z",
  payables:
    "M1.85 6.35h16.3A1.45 1.45 0 0 1 19.6 7.8v7.3a1.45 1.45 0 0 1-1.45 1.45H1.85A1.45 1.45 0 0 1 .4 15.1V7.8A1.45 1.45 0 0 1 1.85 6.35z",
  payments:
    "M10 1.75a8.25 8.25 0 1 1 0 16.5 8.25 8.25 0 0 1 0-16.5zm3.55 5.2-4.85 5.5-2.4-2.4-1.35 1.35 3.75 3.75 6.2-7.05-1.35-1.15z",
  shipments:
    "M1.7 8.2h9.2V4.4l7.4 4.4-7.4 4.4V9.6H1.7V8.2zM2.2 13.4h15.6v2.4H2.2z",
  customs:
    "M8.85 1.7a6.55 6.55 0 1 1 0 13.1 6.55 6.55 0 0 1 0-13.1zm4.5 10.5 4.7 4.7c.45.45.45 1.18 0 1.63l-1.15 1.15",
  inventory: "M5.7 2.15h8.6v5.5H5.7V2.15zM3.15 8.35h13.7v9.5H3.15V8.35z",
  users:
    "M7.2 2.4a2.7 2.7 0 1 1 0 5.4 2.7 2.7 0 0 1 0-5.4zm6.1 1.1a2.3 2.3 0 1 1 0 4.6 2.3 2.3 0 0 1 0-4.6zM2.6 16.3c.35-3 2.7-4.9 5.7-4.9 3 0 5.35 1.9 5.7 4.9H2.6z",
};

const NAV = [
  {
    id: "compras",
    title: "Compras",
    items: [
      { href: "#/compras/pedidos", label: "Pedidos", icon: "orders" },
      { href: "#/compras/faturas", label: "Faturas", icon: "invoices" },
      { href: "#/compras/ingestao", label: "Ingestão", icon: "ingestion" },
    ],
  },
  {
    id: "financeiro",
    title: "Financeiro",
    items: [
      { href: "#/financeiro/payables", label: "Contas a pagar", icon: "payables" },
      { href: "#/financeiro/payments", label: "Pagamentos realizados", icon: "payments" },
    ],
  },
  {
    id: "logistica",
    title: "Logística",
    items: [{ href: "#/logistica/embarques", label: "Embarques", icon: "shipments" }],
  },
  {
    id: "aduana",
    title: "Aduana",
    items: [
      { href: "#/aduana/processos", label: "Processos", icon: "customs" },
      { href: "#/aduana/estoque", label: "Estoque", icon: "inventory" },
    ],
  },
  {
    id: "catalogo",
    title: "Catálogo",
    items: [{ href: "#/catalog/products", label: "Produtos", icon: "products" }],
  },
  {
    id: "admin",
    title: "Administração",
    items: [{ href: "#/admin/users", label: "Usuários", icon: "users" }],
  },
];

const ROLE = { admin: "Administrador", operator: "Operador", viewer: "Leitura" };

let DATA = null;
let debounceTimer = 0;
let loading = false;
let menuOpen = false;
let moreOpen = false;
let notice = null;

function $(sel, root = document) {
  return root.querySelector(sel);
}

function icon(name) {
  return `<svg class="nav-icon" viewBox="0 0 20 20" aria-hidden="true"><path fill="currentColor" d="${ICONS[name]}"></path></svg>`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function parseRoute() {
  const raw = location.hash.slice(1) || "/catalog/products";
  const [pathPart, queryPart] = raw.split("?");
  const path = pathPart.startsWith("/") ? pathPart : `/${pathPart}`;
  return { path, params: new URLSearchParams(queryPart || "") };
}

function go(path, params) {
  const query = params && [...params].length ? `?${params}` : "";
  location.hash = `#${path}${query}`;
}

function listQueryFromParams(params) {
  const next = new URLSearchParams();
  for (const key of ["q", "active", "incomplete", "missing_ncm", "size", "color", "origin", "sort", "offset", "row", "demo"]) {
    const value = params.get(key);
    if (value) next.set(key, value);
  }
  return next;
}

function persist() {
  sessionStorage.setItem(
    SESSION_KEY,
    JSON.stringify({ products: DATA.products, nextId: DATA.nextId, notice }),
  );
}

function restoreSession(base) {
  const saved = sessionStorage.getItem(SESSION_KEY);
  if (!saved) return base;
  try {
    const parsed = JSON.parse(saved);
    if (Array.isArray(parsed.products) && parsed.products.length) {
      base.products = parsed.products;
      base.nextId = parsed.nextId || Math.max(...parsed.products.map((p) => p.id)) + 1;
    }
  } catch {
    /* ignore */
  }
  return base;
}

function isIncomplete(product) {
  return !product.ncm || !product.ean || product.quality_unknown;
}

function isGenericDesc(product) {
  const description = (product.description || "").trim();
  if (!description) return true;
  if (description === product.sku) return true;
  if (/^item\s/i.test(description)) return true;
  if (/^sku\s/i.test(description)) return true;
  return false;
}

function identity(product) {
  if (isGenericDesc(product)) {
    return { title: product.sku, sub: "Sem descrição comercial", fallback: true };
  }
  const bits = [];
  bits.push(product.sku);
  if (product.size) bits.push(product.size);
  if (product.color) bits.push(product.color);
  if (product.ean && product.ean !== product.sku) bits.push(product.ean);
  return { title: product.description, sub: bits.join(" · "), fallback: false };
}

function dash(value) {
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

function uniqueValues(products, key) {
  return [...new Set(products.map((p) => p[key]).filter(Boolean))].sort();
}

function applyFilters(params) {
  let rows = DATA.products.slice();
  if (params.get("demo") === "empty") return [];
  const q = (params.get("q") || "").trim().toLowerCase();
  if (q) {
    rows = rows.filter((p) => {
      const hay = [p.sku, p.description, p.ean, p.ncm, p.size, p.color, p.nome_produto]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }
  if (params.get("active") === "1") rows = rows.filter((p) => p.is_active);
  if (params.get("active") === "0") rows = rows.filter((p) => !p.is_active);
  if (params.get("incomplete") === "1") rows = rows.filter(isIncomplete);
  if (params.get("missing_ncm") === "1") rows = rows.filter((p) => !p.ncm);
  const sizes = (params.get("size") || "").split(",").filter(Boolean);
  if (sizes.length) rows = rows.filter((p) => sizes.includes(p.size));
  const colors = (params.get("color") || "").split(",").filter(Boolean);
  if (colors.length) rows = rows.filter((p) => colors.includes(p.color));
  const origins = (params.get("origin") || "").split(",").filter(Boolean);
  if (origins.length) rows = rows.filter((p) => origins.includes(p.country_of_origin));
  const sort = params.get("sort") || "description";
  rows.sort((a, b) => {
    if (sort === "sku") return a.sku.localeCompare(b.sku);
    if (sort === "quality") return Number(isIncomplete(b)) - Number(isIncomplete(a)) || identity(a).title.localeCompare(identity(b).title);
    return identity(a).title.localeCompare(identity(b).title, "pt");
  });
  return rows;
}

function counts() {
  const all = DATA.products;
  return {
    total: all.length,
    incomplete: all.filter(isIncomplete).length,
    missing_ncm: all.filter((p) => !p.ncm).length,
    active: all.filter((p) => p.is_active).length,
  };
}

function renderSidebar(path) {
  const html = NAV.map((group) => {
    const items = group.items
      .map((item) => {
        const route = item.href.slice(1);
        const active = path === route || path.startsWith(`${route}/`);
        return `<a href="${item.href}" class="${active ? "active" : ""}" title="${item.label}" aria-label="${item.label}">${icon(item.icon)}<span class="nav-label">${item.label}</span></a>`;
      })
      .join("");
    return `<div class="nav-group"><div class="nav-group-title">${group.title}</div>${items}</div>`;
  }).join("");
  $("#sidebar").innerHTML = `
    <div>
      <div class="brand-full">Epic Controle</div>
      <div class="brand-rail" aria-hidden="true">EC</div>
      <div class="brand-user">Administrador · proto</div>
    </div>
    <nav class="side-nav" aria-label="Módulos">${html}</nav>
    <div class="side-footer">
      EUR/BRL 6,12
      <div class="fx-strip">FX · leitura</div>
    </div>`;
}

function btn(label, { href, primary, ghost, danger, id, type = "button" } = {}) {
  const cls = ["btn", primary ? "btn-primary" : "", ghost ? "btn-ghost" : "", danger ? "btn-danger" : ""]
    .filter(Boolean)
    .join(" ");
  if (href) return `<a class="${cls}" href="${href}" ${id ? `data-testid="${id}"` : ""}>${label}</a>`;
  return `<button type="${type}" class="${cls}" ${id ? `data-testid="${id}"` : ""}>${label}</button>`;
}

function renderNotice() {
  if (!notice) return "";
  return `<div class="notice notice-${notice.tone}" role="status">${escapeHtml(notice.text)}</div>`;
}

function setParam(params, key, value) {
  const next = new URLSearchParams(params);
  if (!value) next.delete(key);
  else next.set(key, value);
  next.delete("offset");
  go("/catalog/products", next);
}

function toggleCsvParam(params, key, token) {
  const current = (params.get(key) || "").split(",").filter(Boolean);
  const nextVals = current.includes(token) ? current.filter((v) => v !== token) : [...current, token];
  setParam(params, key, nextVals.join(","));
}

function hasQuery(params) {
  return Boolean(
    params.get("q") ||
      params.get("active") ||
      params.get("incomplete") ||
      params.get("missing_ncm") ||
      params.get("size") ||
      params.get("color") ||
      params.get("origin") ||
      params.get("demo"),
  );
}

function productListView(params) {
  const c = counts();
  const filtered = applyFilters(params);
  const offset = Number(params.get("offset") || "0") || 0;
  const pageRows = filtered.slice(offset, offset + PAGE);
  const selected = params.get("row");
  const q = params.get("q") || "";
  const sizes = uniqueValues(DATA.products, "size");
  const colors = uniqueValues(DATA.products, "color");
  const origins = uniqueValues(DATA.products, "country_of_origin");
  const emptyCatalog = params.get("demo") === "empty";
  const noResults = !emptyCatalog && filtered.length === 0 && hasQuery(params);
  const trulyEmpty = !emptyCatalog && DATA.products.length === 0;

  const chips = [];
  if (q) chips.push({ key: "q", label: `Busca: ${q}` });
  if (params.get("active") === "1") chips.push({ key: "active", label: "Ativos" });
  if (params.get("active") === "0") chips.push({ key: "active", label: "Inativos" });
  if (params.get("incomplete") === "1") chips.push({ key: "incomplete", label: "Dados incompletos" });
  if (params.get("missing_ncm") === "1") chips.push({ key: "missing_ncm", label: "Sem NCM" });
  for (const size of (params.get("size") || "").split(",").filter(Boolean)) {
    chips.push({ key: "size", token: size, label: `Tamanho: ${size}` });
  }
  for (const color of (params.get("color") || "").split(",").filter(Boolean)) {
    chips.push({ key: "color", token: color, label: `Cor: ${color}` });
  }
  for (const origin of (params.get("origin") || "").split(",").filter(Boolean)) {
    chips.push({ key: "origin", token: origin, label: `Origem: ${origin}` });
  }
  if (emptyCatalog) chips.push({ key: "demo", label: "Catálogo vazio (simulação)" });

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const pageIndex = Math.floor(offset / PAGE);

  let body;
  if (loading) {
    body = `<div class="skeleton" data-testid="products-skeleton">${"<div class='sk'></div>".repeat(8)}</div>`;
  } else if (emptyCatalog || trulyEmpty) {
    body = `<div class="empty" data-testid="empty-catalog"><h2>Catálogo vazio</h2><p>Cadastre o primeiro produto para usá-lo nos pedidos.</p><p style="margin-top:12px">${btn("Novo produto", { href: "#/catalog/products/new", primary: true, id: "products-new-cta" })}</p></div>`;
  } else if (noResults) {
    body = `<div class="empty" data-testid="no-results"><h2>Nenhum resultado</h2><p>Nenhum produto corresponde à busca ou aos filtros. Ajuste a consulta ou limpe os filtros.</p></div>`;
  } else {
    const rowsHtml = pageRows
      .map((p) => {
        const idn = identity(p);
        const quality = isIncomplete(p)
          ? `<span class="badge badge-warning">Incompleto</span>`
          : `<span class="badge badge-info">Completo</span>`;
        const status = p.is_active
          ? `<span class="badge badge-success">Ativo</span>`
          : `<span class="badge badge-neutral">Inativo</span>`;
        const fiscal = p.ncm ? p.ncm : "—";
        return `<tr class="${String(p.id) === selected ? "selected" : ""}" data-id="${p.id}" tabindex="0">
          <td><div class="cell-primary">${escapeHtml(idn.title)}${idn.fallback ? ` <span class="fallback-note">· ${escapeHtml(idn.sub)}</span>` : ""}</div>${idn.fallback ? "" : `<div class="cell-secondary">${escapeHtml(idn.sub)}</div>`}</td>
          <td>${escapeHtml(fiscal)}</td>
          <td>${quality}</td>
          <td>${status}</td>
        </tr>`;
      })
      .join("");
    const pageButtons = Array.from({ length: pages }, (_, i) => {
      const off = i * PAGE;
      return `<button type="button" class="btn" data-page="${off}" aria-current="${i === pageIndex ? "page" : undefined}">${i + 1}</button>`;
    }).join("");
    body = `
      <div class="table-wrap">
        <table class="op" data-testid="products-table">
          <thead><tr><th>Produto</th><th>NCM</th><th>Qualidade</th><th>Situação</th></tr></thead>
          <tbody>${rowsHtml}</tbody>
        </table>
      </div>
      <div class="pagination">
        <span data-testid="products-total">${filtered.length} resultado${filtered.length === 1 ? "" : "s"} · página ${pageIndex + 1} de ${pages}</span>
        <div class="page-btns">
          <button type="button" class="btn" data-page="${Math.max(0, offset - PAGE)}" ${offset === 0 ? "disabled" : ""}>Anterior</button>
          ${pageButtons}
          <button type="button" class="btn" data-page="${offset + PAGE}" ${offset + PAGE >= filtered.length ? "disabled" : ""}>Próxima</button>
        </div>
      </div>`;
  }

  const moreFacets = [];
  if (sizes.length) {
    moreFacets.push(`<fieldset class="facet"><legend>Tamanho</legend>${sizes
      .map((s) => `<label><input type="checkbox" data-facet="size" value="${escapeHtml(s)}" ${(params.get("size") || "").split(",").includes(s) ? "checked" : ""}> ${escapeHtml(s)}</label>`)
      .join("")}</fieldset>`);
  }
  if (colors.length) {
    moreFacets.push(`<fieldset class="facet"><legend>Cor</legend>${colors
      .map((s) => `<label><input type="checkbox" data-facet="color" value="${escapeHtml(s)}" ${(params.get("color") || "").split(",").includes(s) ? "checked" : ""}> ${escapeHtml(s)}</label>`)
      .join("")}</fieldset>`);
  }
  if (origins.length) {
    moreFacets.push(`<fieldset class="facet"><legend>Origem</legend>${origins
      .map((s) => `<label><input type="checkbox" data-facet="origin" value="${escapeHtml(s)}" ${(params.get("origin") || "").split(",").includes(s) ? "checked" : ""}> ${escapeHtml(s)}</label>`)
      .join("")}</fieldset>`);
  }

  return `
    <section class="panel" data-testid="product-list-page">
      <div class="breadcrumb">Catálogo / Produtos</div>
      <div class="page-header">
        <div>
          <h1>Produtos</h1>
          <p class="subtitle">Cadastro mestre · descoberta por descrição, SKU, EAN ou NCM</p>
        </div>
        <div class="header-actions">
          <div class="overflow">
            ${btn("⋯", { ghost: true, id: "catalog-overflow" })}
            ${
              menuOpen
                ? `<div class="menu" role="menu">
                    <a href="#/catalog/suppliers/26">Fornecedor principal · Heroe's Srl</a>
                    <div class="sep"></div>
                    <button type="button" class="future" data-action="future">Selecionar produto · FUTURO</button>
                    <button type="button" data-action="empty">${emptyCatalog ? "Sair da simulação vazia" : "Simular catálogo vazio"}</button>
                  </div>`
                : ""
            }
          </div>
          ${btn("+ Novo produto", { href: "#/catalog/products/new", primary: true, id: "products-new-cta" })}
        </div>
      </div>
      ${renderNotice()}
      <div class="kpis">
        <button type="button" class="kpi ${!hasQuery(params) || (!params.get("incomplete") && !params.get("missing_ncm") && !params.get("active")) ? "" : ""}" data-kpi="all">
          <span class="kpi-label">Produtos</span>
          <span class="kpi-value">${c.total}</span>
        </button>
        <button type="button" class="kpi ${params.get("incomplete") === "1" ? "active" : ""}" data-kpi="incomplete">
          <span class="kpi-label">Dados incompletos</span>
          <span class="kpi-value">${c.incomplete}</span>
        </button>
        <button type="button" class="kpi ${params.get("missing_ncm") === "1" ? "active" : ""}" data-kpi="missing_ncm">
          <span class="kpi-label">Sem NCM</span>
          <span class="kpi-value">${c.missing_ncm}</span>
        </button>
      </div>
      <div class="filter-bar">
        <div class="filter-primary">
          <div class="search-wrap">
            <svg class="search-icon" viewBox="0 0 20 20" aria-hidden="true"><path fill="currentColor" d="M8.2 1.8a6.4 6.4 0 1 1 0 12.8 6.4 6.4 0 0 1 0-12.8zm5.2 10.4 4.4 4.4-1.4 1.4-4.4-4.4 1.4-1.4z"/></svg>
            <input data-testid="products-search" type="search" value="${escapeHtml(q)}" placeholder="Buscar por descrição, SKU, EAN ou NCM" aria-label="Buscar produtos" />
          </div>
          <button type="button" class="chip" data-quick="active-1" aria-pressed="${params.get("active") === "1"}">Ativos</button>
          <button type="button" class="chip" data-quick="active-0" aria-pressed="${params.get("active") === "0"}">Inativos</button>
          <button type="button" class="chip" data-quick="incomplete" aria-pressed="${params.get("incomplete") === "1"}">Dados incompletos</button>
          <button type="button" class="chip" data-quick="missing_ncm" aria-pressed="${params.get("missing_ncm") === "1"}">Sem NCM</button>
          <button type="button" class="chip" data-testid="more-filters" aria-pressed="${moreOpen}">Mais filtros</button>
        </div>
        ${
          moreOpen
            ? `<div class="more-panel" data-testid="more-panel"><div class="more-grid">${moreFacets.join("") || "<p class='stub'>Não há valores de tamanho, cor ou origem nesta fixture para facetar.</p>"}</div></div>`
            : ""
        }
        ${
          chips.length
            ? `<div class="chips">${chips
                .map(
                  (chip) =>
                    `<span class="chip-removable">${escapeHtml(chip.label)}<button type="button" data-remove="${chip.key}" data-token="${chip.token || ""}" aria-label="Remover ${escapeHtml(chip.label)}">×</button></span>`,
                )
                .join("")}<button type="button" class="btn btn-ghost" data-action="clear">Limpar</button></div>`
            : ""
        }
      </div>
      <div class="toolbar-row">
        <span>Ordenar</span>
        <select class="sort" data-testid="products-sort" aria-label="Ordenar">
          <option value="description" ${params.get("sort") === "description" || !params.get("sort") ? "selected" : ""}>Descrição</option>
          <option value="sku" ${params.get("sort") === "sku" ? "selected" : ""}>SKU</option>
          <option value="quality" ${params.get("sort") === "quality" ? "selected" : ""}>Qualidade (incompletos primeiro)</option>
        </select>
      </div>
      ${body}
    </section>`;
}

function bindProductList(params) {
  const search = $('[data-testid="products-search"]');
  if (search) {
    search.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(() => {
        setParam(params, "q", search.value.trim());
      }, DEBOUNCE_MS);
    });
    search.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        search.value = "";
        setParam(params, "q", "");
      }
    });
  }
  document.querySelectorAll("[data-quick]").forEach((el) => {
    el.addEventListener("click", () => {
      const key = el.getAttribute("data-quick");
      if (key === "active-1") setParam(params, "active", params.get("active") === "1" ? "" : "1");
      if (key === "active-0") setParam(params, "active", params.get("active") === "0" ? "" : "0");
      if (key === "incomplete") setParam(params, "incomplete", params.get("incomplete") === "1" ? "" : "1");
      if (key === "missing_ncm") setParam(params, "missing_ncm", params.get("missing_ncm") === "1" ? "" : "1");
    });
  });
  const more = $('[data-testid="more-filters"]');
  if (more) {
    more.addEventListener("click", () => {
      moreOpen = !moreOpen;
      render();
    });
  }
  document.querySelectorAll("[data-facet]").forEach((el) => {
    el.addEventListener("change", () => toggleCsvParam(params, el.getAttribute("data-facet"), el.value));
  });
  document.querySelectorAll("[data-remove]").forEach((el) => {
    el.addEventListener("click", () => {
      const key = el.getAttribute("data-remove");
      const token = el.getAttribute("data-token");
      if (token) {
        const current = (params.get(key) || "").split(",").filter((v) => v && v !== token);
        setParam(params, key, current.join(","));
      } else setParam(params, key, "");
    });
  });
  const clear = $("[data-action='clear']");
  if (clear) clear.addEventListener("click", () => go("/catalog/products"));
  const sort = $('[data-testid="products-sort"]');
  if (sort) {
    sort.addEventListener("change", () => setParam(params, "sort", sort.value === "description" ? "" : sort.value));
  }
  document.querySelectorAll("[data-page]").forEach((el) => {
    el.addEventListener("click", () => {
      const next = new URLSearchParams(params);
      const off = Number(el.getAttribute("data-page"));
      if (off <= 0) next.delete("offset");
      else next.set("offset", String(off));
      go("/catalog/products", next);
    });
  });
  document.querySelectorAll("[data-kpi]").forEach((el) => {
    el.addEventListener("click", () => {
      const kind = el.getAttribute("data-kpi");
      if (kind === "all") go("/catalog/products");
      if (kind === "incomplete") setParam(params, "incomplete", "1");
      if (kind === "missing_ncm") setParam(params, "missing_ncm", "1");
    });
  });
  document.querySelectorAll("[data-testid='products-table'] tbody tr").forEach((row) => {
    const open = () => {
      const id = row.getAttribute("data-id");
      const next = listQueryFromParams(params);
      next.set("row", id);
      sessionStorage.setItem("mdm-ux-r-return", `/catalog/products?${next}`);
      go(`/catalog/products/${id}`, next);
    };
    row.addEventListener("click", open);
    row.addEventListener("keydown", (event) => {
      if (event.key === "Enter") open();
    });
  });
  const overflow = $('[data-testid="catalog-overflow"]');
  if (overflow) {
    overflow.addEventListener("click", (event) => {
      event.stopPropagation();
      menuOpen = !menuOpen;
      render();
    });
  }
  const menu = $(".menu");
  if (menu) menu.addEventListener("click", (event) => event.stopPropagation());
  const future = $("[data-action='future']");
  if (future) future.addEventListener("click", () => go("/futuro/selecionar", listQueryFromParams(params)));
  const empty = $("[data-action='empty']");
  if (empty) {
    empty.addEventListener("click", () => {
      if (params.get("demo") === "empty") setParam(params, "demo", "");
      else setParam(params, "demo", "empty");
    });
  }
}

function returnHref() {
  return `#${sessionStorage.getItem("mdm-ux-r-return") || "/catalog/products"}`;
}

function productById(id) {
  return DATA.products.find((p) => String(p.id) === String(id));
}

function productDetailView(product, editing) {
  const idn = identity(product);
  const status = product.is_active
    ? `<span class="badge badge-success">Ativo</span>`
    : `<span class="badge badge-neutral">Inativo</span>`;
  const quality = isIncomplete(product)
    ? `<span class="badge badge-warning">Incompleto</span>`
    : `<span class="badge badge-info">Completo</span>`;
  const readRow = (label, value) =>
    `<div class="dl"><dt>${label}</dt><dd class="${value ? "" : "empty"}">${escapeHtml(dash(value))}</dd></div>`;

  if (!editing) {
    return `
      <section class="panel" data-testid="product-detail-page">
        <div class="breadcrumb"><a href="${returnHref()}">Produtos</a> / ${escapeHtml(idn.title)}</div>
        <div class="page-header">
          <div>
            <h1>${escapeHtml(idn.title)}</h1>
            <p class="subtitle">${escapeHtml(idn.sub)}</p>
          </div>
          <div class="header-actions">
            ${btn("Voltar à lista", { href: returnHref(), ghost: true, id: "product-back" })}
            ${btn("Editar", { href: `#/catalog/products/${product.id}/edit`, primary: true, id: "product-edit" })}
          </div>
        </div>
        <div>${status} ${quality}</div>
        ${idn.fallback ? `<div class="notice notice-warn" style="margin-top:12px">Sem descrição comercial — o SKU é a única identidade humana disponível neste registro.</div>` : ""}
        <div class="section"><h2>Visão geral</h2>
          ${readRow("SKU", product.sku)}
          ${readRow("Descrição", product.description)}
          ${readRow("Situação", product.is_active ? "Ativo" : "Inativo")}
        </div>
        <div class="section"><h2>Características</h2>
          ${readRow("Tamanho", product.size)}
          ${readRow("Cor", product.color)}
        </div>
        <div class="section"><h2>Fiscal / aduana</h2>
          ${readRow("NCM", product.ncm)}
          ${readRow("EAN", product.ean)}
          ${readRow("Origem", product.country_of_origin)}
          ${readRow("Unidade", product.unit)}
        </div>
        <div class="section"><h2>Físico</h2>
          ${readRow("Peso líquido (kg)", product.net_weight_kg)}
        </div>
        <div class="section"><h2>Auditoria</h2>
          <p class="stub">Representação visual · fixture local · sem eventos reais.</p>
          <div class="dl"><dt>Origem do registro</dt><dd>${product.source === "proto-fake" ? "Fake do protótipo" : "Fixture visual CSV V1 (somente leitura)"}</dd></div>
        </div>
      </section>`;
  }

  return `
    <section class="panel" data-testid="product-edit-page">
      <div class="breadcrumb"><a href="${returnHref()}">Produtos</a> / ${escapeHtml(idn.title)} / Editar</div>
      <div class="page-header">
        <div>
          <h1>Editar produto</h1>
          <p class="subtitle meta-id">${escapeHtml(product.sku)}</p>
        </div>
        <div class="header-actions">
          ${btn("Cancelar", { href: `#/catalog/products/${product.id}`, ghost: true })}
        </div>
      </div>
      ${renderNotice()}
      <form data-testid="product-edit-form">
        <div class="section"><h2>Visão geral</h2>
          <div class="form-grid">
            <div class="field"><label>SKU</label><input value="${escapeHtml(product.sku)}" readonly></div>
            <div class="field span-2"><label for="e-desc">Descrição</label><input id="e-desc" name="description" value="${escapeHtml(product.description || "")}"></div>
          </div>
        </div>
        <div class="section"><h2>Características</h2>
          <div class="form-grid">
            <div class="field"><label for="e-size">Tamanho</label><input id="e-size" name="size" value="${escapeHtml(product.size || "")}"></div>
            <div class="field"><label for="e-color">Cor</label><input id="e-color" name="color" value="${escapeHtml(product.color || "")}"></div>
          </div>
        </div>
        <div class="section"><h2>Fiscal / aduana</h2>
          <div class="form-grid">
            <div class="field"><label for="e-ncm">NCM</label><input id="e-ncm" name="ncm" value="${escapeHtml(product.ncm || "")}"><div class="hint">Oito dígitos</div></div>
            <div class="field"><label for="e-ean">EAN</label><input id="e-ean" name="ean" value="${escapeHtml(product.ean || "")}"></div>
            <div class="field"><label for="e-origin">Origem (ISO-2)</label><input id="e-origin" name="country_of_origin" value="${escapeHtml(product.country_of_origin || "")}"></div>
            <div class="field"><label for="e-unit">Unidade</label><input id="e-unit" name="unit" value="${escapeHtml(product.unit || "")}"></div>
          </div>
        </div>
        <div class="section"><h2>Físico</h2>
          <div class="field" style="max-width:240px"><label for="e-weight">Peso líquido (kg)</label><input id="e-weight" name="net_weight_kg" value="${escapeHtml(product.net_weight_kg ?? "")}"></div>
        </div>
        <div class="section">${btn("Salvar", { primary: true, id: "product-save", type: "submit" })}</div>
      </form>
    </section>`;
}

function productCreateView() {
  return `
    <section class="panel" data-testid="product-create-page">
      <div class="breadcrumb"><a href="${returnHref()}">Produtos</a> / Novo</div>
      <div class="page-header">
        <div>
          <h1>Novo produto</h1>
          <p class="subtitle">SKU e descrição bastam para começar. Detalhes fiscais e físicos ficam para a ficha.</p>
        </div>
        ${btn("Voltar", { href: returnHref(), ghost: true })}
      </div>
      ${renderNotice()}
      <form data-testid="product-create-form">
        <div class="section"><h2>Essenciais</h2>
          <div class="form-grid">
            <div class="field"><label for="c-sku">SKU</label><input id="c-sku" name="sku" required data-testid="product-sku"></div>
            <div class="field span-2"><label for="c-desc">Descrição</label><input id="c-desc" name="description" required data-testid="product-description"></div>
          </div>
        </div>
        <div class="section">${btn("Criar", { primary: true, id: "product-create-submit", type: "submit" })}</div>
      </form>
    </section>`;
}

function supplierView() {
  const s = DATA.supplier;
  return `
    <section class="panel" data-testid="supplier-detail-page">
      <div class="breadcrumb"><a href="#/catalog/products">Catálogo / Produtos</a> / Fornecedor principal</div>
      <div class="page-header">
        <div>
          <h1>${escapeHtml(s.name)}</h1>
          <p class="subtitle">Acesso contextual · não aparece no rail</p>
        </div>
        ${btn("Voltar a Produtos", { href: "#/catalog/products", ghost: true })}
      </div>
      <span class="badge badge-success">Ativo</span>
      <div class="section"><h2>Identidade</h2>
        <div class="dl"><dt>Nome</dt><dd>${escapeHtml(s.name)}</dd></div>
        <div class="dl"><dt>Código</dt><dd>${escapeHtml(s.code)}</dd></div>
      </div>
      <div class="section"><h2>Dados fiscais</h2>
        <div class="dl"><dt>País</dt><dd>${escapeHtml(s.country_code)}</dd></div>
        <div class="dl"><dt>Identificador fiscal</dt><dd class="empty">${dash(s.tax_id)}</dd></div>
      </div>
      <p class="stub">Edição de tax_id na UI de produção já existe e permanece avulsa (B6). Este proto só prova o acesso contextual.</p>
    </section>`;
}

function usersView() {
  const rows = DATA.users
    .map(
      (u) => `<tr data-id="${u.id}">
        <td class="cell-primary">${escapeHtml(u.name)}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${ROLE[u.role] || u.role}</td>
        <td>${u.is_active ? '<span class="badge badge-success">Ativo</span>' : '<span class="badge badge-neutral">Inativo</span>'}</td>
      </tr>`,
    )
    .join("");
  return `
    <section class="panel" data-testid="users-list-page">
      <div class="breadcrumb">Administração / Usuários</div>
      <div class="page-header">
        <div>
          <h1>Usuários</h1>
          <p class="subtitle">Acesso e papéis · IAM-light</p>
        </div>
        ${btn("+ Novo usuário", { primary: true })}
      </div>
      <div class="table-wrap">
        <table class="op">
          <thead><tr><th>Nome</th><th>E-mail</th><th>Papel</th><th>Situação</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>`;
}

function stubView(title, extra = "") {
  return `<section class="panel"><div class="breadcrumb">${escapeHtml(title)}</div><h1>${escapeHtml(title)}</h1><p class="stub">Superfície operacional preservada conceitualmente. Fora do escopo visual MDM-UX-R.</p>${extra}</section>`;
}

function embarquesView() {
  return stubView(
    "Embarques",
    `<div class="section">${btn("Prestadores logísticos", { href: "#/logistica/prestadores", ghost: true, id: "providers-cta" })}<p class="stub">CTA contextual · Prestadores não estão no rail.</p></div>`,
  );
}

function providersView() {
  const p = DATA.logistics_provider;
  return `<section class="panel"><div class="breadcrumb"><a href="#/logistica/embarques">Embarques</a> / Prestadores</div><h1>Prestadores logísticos</h1><p class="subtitle">Chegada só pelo CTA de Embarques</p><div class="section"><div class="dl"><dt>Nome</dt><dd>${escapeHtml(p.name)}</dd></div></div></section>`;
}

function futureView() {
  const cards = DATA.products
    .filter((p) => /starlight|wash bag|olympia/i.test(`${p.description} ${p.sku}`))
    .slice(0, 4)
    .map((p) => {
      const idn = identity(p);
      return `<article class="candidate">
        <div>
          <div class="cell-primary">${escapeHtml(idn.title)}</div>
          <div class="cell-secondary">${escapeHtml(idn.sub)}</div>
          ${isIncomplete(p) ? '<span class="badge badge-warning">Incompleto</span>' : '<span class="badge badge-info">Completo</span>'}
        </div>
        ${btn("Selecionar", { ghost: true })}
      </article>`;
    })
    .join("");
  return `
    <section class="panel" data-testid="future-select">
      <div class="notice notice-warn"><strong>FUTURO</strong> — mock exploratório de seleção assistida. Não há IA, LLM, embeddings nem endpoint. Reusa o Product canônico.</div>
      <div class="breadcrumb"><a href="#/catalog/products">Produtos</a> / Selecionar produto</div>
      <h1>Selecionar produto</h1>
      <p class="subtitle">A mesma representação da lista: descrição, SKU · atributos, qualidade.</p>
      ${cards || "<p class='stub'>Nenhum candidato nesta fixture.</p>"}
    </section>`;
}

function bindCreate() {
  const form = $('[data-testid="product-create-form"]');
  if (!form) return;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const sku = form.sku.value.trim();
    const description = form.description.value.trim();
    if (!sku || !description) {
      notice = { tone: "err", text: "SKU e descrição são obrigatórios." };
      render();
      return;
    }
    const product = {
      id: DATA.nextId++,
      sku,
      description,
      ean: null,
      ncm: null,
      size: null,
      color: null,
      country_of_origin: null,
      unit: null,
      net_weight_kg: null,
      is_active: true,
      quality_unknown: false,
      source: "proto-session",
      enrichment: ["created-in-proto"],
    };
    DATA.products.unshift(product);
    notice = { tone: "ok", text: "Produto criado na sessão do protótipo. Nada foi gravado em epic_v2." };
    persist();
    go(`/catalog/products/${product.id}`);
  });
}

function bindEdit(product) {
  const form = $('[data-testid="product-edit-form"]');
  if (!form) return;
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    product.description = form.description.value.trim();
    product.size = form.size.value.trim() || null;
    product.color = form.color.value.trim() || null;
    product.ncm = form.ncm.value.trim() || null;
    product.ean = form.ean.value.trim() || null;
    product.country_of_origin = form.country_of_origin.value.trim() || null;
    product.unit = form.unit.value.trim() || null;
    product.net_weight_kg = form.net_weight_kg.value.trim() || null;
    notice = { tone: "ok", text: "Alterações só na sessão do protótipo." };
    persist();
    go(`/catalog/products/${product.id}`);
  });
}

function bindGlobal() {
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && event.target.tagName !== "INPUT" && event.target.tagName !== "TEXTAREA") {
      const search = $('[data-testid="products-search"]');
      if (search) {
        event.preventDefault();
        search.focus();
      }
    }
    if (event.key === "Escape") {
      if (menuOpen || moreOpen) {
        menuOpen = false;
        moreOpen = false;
        render();
      }
    }
  });
  document.addEventListener("click", () => {
    if (menuOpen) {
      menuOpen = false;
      render();
    }
  });
}

let globalBound = false;

function render() {
  const { path, params } = parseRoute();
  renderSidebar(path);
  const main = $("#main");
  if (path === "/catalog/products") {
    main.innerHTML = productListView(params);
    bindProductList(params);
    return;
  }
  const detail = path.match(/^\/catalog\/products\/(\d+)$/);
  const edit = path.match(/^\/catalog\/products\/(\d+)\/edit$/);
  if (detail || edit) {
    const product = productById((detail || edit)[1]);
    if (!product) {
      main.innerHTML = `<section class="panel"><h1>Produto não encontrado</h1></section>`;
      return;
    }
    main.innerHTML = productDetailView(product, Boolean(edit));
    if (edit) bindEdit(product);
    return;
  }
  if (path === "/catalog/products/new") {
    main.innerHTML = productCreateView();
    bindCreate();
    return;
  }
  if (path === "/catalog/suppliers/26" || path === "/catalog/suppliers") {
    main.innerHTML = supplierView();
    return;
  }
  if (path === "/admin/users") {
    main.innerHTML = usersView();
    return;
  }
  if (path === "/logistica/embarques") {
    main.innerHTML = embarquesView();
    return;
  }
  if (path === "/logistica/prestadores") {
    main.innerHTML = providersView();
    return;
  }
  if (path === "/futuro/selecionar") {
    main.innerHTML = futureView();
    return;
  }
  const stubs = {
    "/compras/pedidos": "Pedidos",
    "/compras/faturas": "Faturas",
    "/compras/ingestao": "Ingestão",
    "/financeiro/payables": "Contas a pagar",
    "/financeiro/payments": "Pagamentos realizados",
    "/aduana/processos": "Processos aduaneiros",
    "/aduana/estoque": "Estoque",
  };
  main.innerHTML = stubView(stubs[path] || "Protótipo");
}

async function boot() {
  const res = await fetch("./fixtures/catalog-visual.json");
  DATA = restoreSession(await res.json());
  DATA.nextId = DATA.nextId || Math.max(...DATA.products.map((p) => p.id)) + 1;
  if (!location.hash) location.hash = "#/catalog/products";
  if (!globalBound) {
    bindGlobal();
    globalBound = true;
    window.addEventListener("hashchange", () => {
      notice = null;
      menuOpen = false;
      render();
    });
  }
  loading = true;
  render();
  window.setTimeout(() => {
    loading = false;
    render();
  }, 280);
}

boot();
