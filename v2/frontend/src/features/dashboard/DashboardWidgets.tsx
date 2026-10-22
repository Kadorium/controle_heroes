import type { MouseEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  AgingBar,
  BarStack,
  Button,
  EmptyState,
  ErrorState,
  FlowSteps,
  MoneyDisplay,
  SectionCard,
  TrendLine,
} from "../../ui";
import type { AgingCurrencyRow } from "../../ui";
import { formatQuantity, formatRate, formatRelativeDue } from "../../ui/format";
import { statusLabel } from "../../ui/statusLabels";
import type { DashboardWidget } from "./dashboardApi";
import { fetchCommercialAvailability, type CommercialAvailability } from "./dashboardApi";

function asRows(value: unknown): AgingCurrencyRow[] {
  if (!Array.isArray(value)) return [];
  return value.filter((r) => r && typeof r === "object") as AgingCurrencyRow[];
}

function currencyLines(display: Record<string, unknown>, field = "amount") {
  const rows = (display.by_currency as Array<Record<string, unknown>> | undefined) ?? [];
  return rows.map((r) => (
    <div key={String(r.currency)} className="dash-currency-line">
      <span>{String(r.currency)}</span>
      <MoneyDisplay amount={String(r[field] ?? r.amount ?? "0")} currency={String(r.currency)} compact />
    </div>
  ));
}

const LOCATION_LABEL: Record<string, string> = {
  BONDED: "Entreposto",
  DOMESTIC: "Doméstico",
  QUARANTINE: "Quarentena",
};

const MODULE_LABEL: Record<string, string> = {
  billing: "Contas a pagar",
  catalog: "Catálogo",
  ingestion: "Ingestão",
  customs: "Aduana",
  costing: "Custo",
  treasury: "Tesouro",
  orders: "Pedidos",
  inventory: "Estoque",
};

const SEVERITY_LABEL: Record<string, string> = {
  blocker: "Bloqueio",
  overdue: "Vencido",
  due_today: "Vence hoje",
  warning: "Atenção",
};

function WidgetChrome({
  widget,
  onExplain,
  extraAction,
  children,
}: {
  widget: DashboardWidget;
  onExplain: (widget: DashboardWidget) => void;
  extraAction?: ReactNode;
  children: ReactNode;
}) {
  const navigate = useNavigate();
  const cta = widget.cta_label || (widget.drill ? "Abrir" : null);
  function onCardClick(e: MouseEvent) {
    if (!widget.drill) return;
    const t = e.target as HTMLElement;
    if (t.closest("a, button, input, select, textarea")) return;
    navigate(widget.drill);
  }
  return (
    <div
      className={widget.drill ? "dash-widget-hit" : undefined}
      onClick={onCardClick}
      onKeyDown={(e) => {
        if (!widget.drill) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          navigate(widget.drill);
        }
      }}
    >
      <SectionCard
        title={widget.label}
        data-testid={`dash-widget-${widget.widget_id}`}
        actions={
          <div className="dash-widget-actions">
            <button
              type="button"
              className="dash-tip"
              title={widget.short_description}
              aria-label={`O que é ${widget.label}`}
              onClick={() => onExplain(widget)}
            >
              ⓘ
            </button>
            {extraAction}
          </div>
        }
      >
        {children}
        {cta && widget.drill ? (
          <div className="dash-widget-footer">
            <Link className="row-link" to={widget.drill}>
              {cta}
            </Link>
          </div>
        ) : null}
      </SectionCard>
    </div>
  );
}

function CommercialBody({ initial }: { initial: Record<string, unknown> }) {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [productType, setProductType] = useState("");
  const [status, setStatus] = useState("");
  const [sort, setSort] = useState("commercial_name");
  const [data, setData] = useState<CommercialAvailability | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setBusy(true);
    void fetchCommercialAvailability({
      q: q || undefined,
      category: category || undefined,
      product_type: productType || undefined,
      status: status || undefined,
      sort,
      limit: 50,
      offset: 0,
    })
      .then((row) => {
        if (!cancelled) setData(row);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [q, category, productType, status, sort]);

  const view = data ?? (initial as unknown as CommercialAvailability);
  const rows = view.rows ?? [];
  const totals = view.totals ?? {};
  const facets = view.facets ?? {};
  const cats = (facets.category as Array<{ value: string; label: string }>) ?? [];
  const types = (facets.product_type as Array<{ value: string; label: string }>) ?? [];
  const regime = view.by_regime ?? [];
  const chartData = regime.map((r) => ({
    name: LOCATION_LABEL[String(r.location_type)] ?? String(r.location_type),
    qty: Number.parseFloat(String(r.qty ?? "0")) || 0,
  }));

  return (
    <div data-testid="commercial-table">
      <div className="dash-dl">
        <div>
          <dt>SKUs disponíveis</dt>
          <dd>{String(totals.sku_available ?? "—")}</dd>
        </div>
        <div>
          <dt>Unidades</dt>
          <dd>{formatQuantity(String(totals.units_available ?? ""))}</dd>
        </div>
        <div>
          <dt>Chegando</dt>
          <dd>{String(totals.sku_incoming ?? "—")}</dd>
        </div>
        <div>
          <dt>Com pendência</dt>
          <dd>{String(totals.sku_attention ?? "—")}</dd>
        </div>
      </div>
      {chartData.some((d) => d.qty > 0) ? (
        <BarStack
          data={chartData}
          xKey="name"
          series={[{ key: "qty", label: "Quantidade" }]}
          stacked={false}
          height={180}
          valueKind="quantity"
        />
      ) : null}
      <div className="filter-bar dash-inline-filters">
        <label>
          Busca
          <input value={q} onChange={(e) => setQ(e.target.value)} />
        </label>
        <label>
          Categoria
          <select value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">Todas</option>
            {cats.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Tipo
          <select value={productType} onChange={(e) => setProductType(e.target.value)}>
            <option value="">Todos</option>
            {types.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          Situação
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todas</option>
            <option value="available">Disponível</option>
            <option value="incoming">Chegando</option>
            <option value="attention">Com pendência</option>
          </select>
        </label>
      </div>
      {busy ? <p className="muted">Atualizando…</p> : null}
      {view.empty ? (
        <EmptyState message="Nenhum produto neste recorte." />
      ) : (
        <div className="dash-table-wrap table-wrap">
          <table className="operational-table">
            <thead>
              <tr>
                <th>
                  <button type="button" className="btn-ghost" onClick={() => setSort("commercial_name")}>
                    Produto
                  </button>
                </th>
                <th>Categoria</th>
                <th>
                  <button type="button" className="btn-ghost" onClick={() => setSort("-available")}>
                    Disponível
                  </button>
                </th>
                <th>Entreposto</th>
                <th>Quarentena</th>
                <th>Liberado não recebido</th>
                <th>
                  <button type="button" className="btn-ghost" onClick={() => setSort("-incoming")}>
                    Entrada prevista
                  </button>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.product_id} data-testid={`commercial-row-${r.product_id}`}>
                  <td>
                    <Link to={r.href}>{r.commercial_name || r.sku}</Link>
                  </td>
                  <td>{r.category ?? "—"}</td>
                  <td>{formatQuantity(r.available_qty)}</td>
                  <td>{formatQuantity(r.bonded_qty)}</td>
                  <td>{formatQuantity(r.quarantine_qty)}</td>
                  <td>{formatQuantity(r.cleared_not_received_qty)}</td>
                  <td>{r.incoming_qty == null ? "—" : formatQuantity(r.incoming_qty)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {view.footer ? (
        <p className="muted">
          {view.footer.label}: {formatQuantity(view.footer.qty)}
        </p>
      ) : null}
    </div>
  );
}

function ExceptionsBody({ display, onSeeAll }: { display: Record<string, unknown>; onSeeAll?: () => void }) {
  const [severity, setSeverity] = useState("");
  const [module, setModule] = useState("");
  const items = useMemo(() => {
    const all = (display.items as Array<Record<string, unknown>> | undefined) ?? [];
    return all.filter((it) => {
      if (severity && String(it.severity) !== severity) return false;
      if (module && String(it.module) !== module) return false;
      return true;
    });
  }, [display.items, severity, module]);
  const bySev = (display.by_severity as Array<Record<string, unknown>> | undefined) ?? [];
  const byMod = (display.by_module as Array<Record<string, unknown>> | undefined) ?? [];
  return (
    <div data-testid="control-exceptions">
      <div className="dash-dl">
        {bySev.map((s) => (
          <div key={String(s.severity)}>
            <dt>{SEVERITY_LABEL[String(s.severity)] ?? String(s.severity)}</dt>
            <dd>{String(s.count)}</dd>
          </div>
        ))}
      </div>
      {byMod.length ? (
        <BarStack
          data={byMod.map((m) => ({
            name: MODULE_LABEL[String(m.module)] ?? String(m.module),
            count: Number(m.count) || 0,
          }))}
          xKey="name"
          series={[{ key: "count", label: "Itens" }]}
          stacked={false}
          height={180}
          valueKind="quantity"
        />
      ) : null}
      <div className="filter-bar dash-inline-filters">
        <label>
          Gravidade
          <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
            <option value="">Todas</option>
            <option value="blocker">Bloqueio</option>
            <option value="overdue">Vencido</option>
            <option value="warning">Atenção</option>
          </select>
        </label>
        <label>
          Módulo
          <select value={module} onChange={(e) => setModule(e.target.value)}>
            <option value="">Todos</option>
            {byMod.map((m) => (
              <option key={String(m.module)} value={String(m.module)}>
                {MODULE_LABEL[String(m.module)] ?? String(m.module)}
              </option>
            ))}
          </select>
        </label>
        {onSeeAll && items.length > 0 ? (
          <Button type="button" variant="ghost" onClick={onSeeAll}>
            Ver todos
          </Button>
        ) : null}
      </div>
      {items.length === 0 ? (
        <EmptyState message={String(display.empty_copy ?? "Nada precisa da sua decisão agora.")} />
      ) : (
        <ul className="dash-inbox">
          {items.map((it, idx) => (
            <li key={`${it.kind}-${it.entity_id}-${idx}`}>
              <span className={`dash-sev dash-sev--${String(it.severity)}`}>
                {SEVERITY_LABEL[String(it.severity)] ?? String(it.severity)}
              </span>{" "}
              {it.href ? (
                <Link to={String(it.href)}>
                  <strong>{String(it.title)}</strong>
                </Link>
              ) : (
                <strong>{String(it.title)}</strong>
              )}
              <span className="muted"> {String(it.reason)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function DashboardWidgetCard({
  widget,
  onExplain,
  onSeeAll,
  compactMoney = true,
}: {
  widget: DashboardWidget;
  onExplain: (widget: DashboardWidget) => void;
  onSeeAll?: (widget: DashboardWidget) => void;
  compactMoney?: boolean;
}) {
  const display = widget.display ?? {};

  if (widget.error || display.state === "error") {
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        <ErrorState message="Não foi possível montar este bloco." />
      </WidgetChrome>
    );
  }

  if (widget.widget_id === "attention.inbox" || widget.kind === "inbox") {
    const items = (display.items as Array<Record<string, unknown>> | undefined) ?? [];
    const total = Number(display.total_count ?? 0);
    const copy = String(display.empty_copy ?? "Nada precisa da sua decisão agora.");
    return (
      <WidgetChrome
        widget={widget}
        onExplain={onExplain}
        extraAction={
          total > items.length && onSeeAll ? (
            <Button type="button" variant="ghost" onClick={() => onSeeAll(widget)}>
              Ver todos
            </Button>
          ) : null
        }
      >
        <p className="muted">
          {total} {total === 1 ? "item" : "itens"}
        </p>
        {items.length === 0 ? (
          <EmptyState message={copy} />
        ) : (
          <ul className="dash-inbox">
            {items.map((it, idx) => (
              <li key={`${it.item_type ?? it.kind}-${idx}`}>
                {it.href ? (
                  <Link to={String(it.href)}>
                    <strong>{String(it.title)}</strong>
                  </Link>
                ) : (
                  <strong>{String(it.title)}</strong>
                )}
                <span className="muted"> {String(it.reason)}</span>
                {it.amount ? (
                  <MoneyDisplay
                    amount={String(it.amount)}
                    currency={it.currency ? String(it.currency) : undefined}
                    compact={compactMoney}
                  />
                ) : null}
              </li>
            ))}
          </ul>
        )}
      </WidgetChrome>
    );
  }

  if (widget.widget_id === "ap.cash_committed") {
    const rows = (display.by_currency as Array<Record<string, unknown>> | undefined) ?? [];
    const labels = (display.labels as Record<string, string> | undefined) ?? {};
    if (display.empty) {
      return (
        <WidgetChrome widget={widget} onExplain={onExplain}>
          <EmptyState message={String(display.message ?? "Nada a vencer neste recorte.")} />
          <p className="muted">inclui vencidas</p>
        </WidgetChrome>
      );
    }
    const chartRows = rows.flatMap((row) => {
      const buckets = (row.buckets as Record<string, string>) ?? {};
      return [
        {
          name: `${labels.overdue ?? "Vencido"} · ${row.currency}`,
          overdue: Number.parseFloat(buckets.overdue ?? "0") || 0,
          m0: Number.parseFloat(buckets.m0 ?? "0") || 0,
          m1: Number.parseFloat(buckets.m1 ?? "0") || 0,
          m2: Number.parseFloat(buckets.m2 ?? "0") || 0,
        },
      ];
    });
    const monthRows =
      rows.length === 1
        ? ["overdue", "m0", "m1", "m2"].map((k) => {
            const buckets = (rows[0].buckets as Record<string, string>) ?? {};
            return { name: labels[k] ?? k, valor: Number.parseFloat(buckets[k] ?? "0") || 0 };
          })
        : chartRows;
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        <p className="muted">inclui vencidas</p>
        {rows.length === 1 ? (
          <BarStack
            data={monthRows}
            xKey="name"
            series={[{ key: "valor", label: String(rows[0].currency) }]}
            stacked={false}
            valueKind="money"
          />
        ) : (
          <BarStack
            data={chartRows}
            xKey="name"
            series={[
              { key: "overdue", label: labels.overdue ?? "Vencido" },
              { key: "m0", label: labels.m0 ?? "Mês" },
              { key: "m1", label: labels.m1 ?? "M+1" },
              { key: "m2", label: labels.m2 ?? "M+2" },
            ]}
            valueKind="money"
          />
        )}
        {rows.map((row) => {
          const buckets = (row.buckets as Record<string, string>) ?? {};
          const total = ["overdue", "m0", "m1", "m2"].reduce(
            (s, k) => s + (Number.parseFloat(buckets[k] ?? "0") || 0),
            0,
          );
          return (
            <p key={String(row.currency)} className="dash-kpis-meta">
              {String(row.currency)}{" "}
              <MoneyDisplay amount={String(total)} currency={String(row.currency)} compact={compactMoney} />
            </p>
          );
        })}
      </WidgetChrome>
    );
  }

  if (widget.kind === "fx_trend" || widget.widget_id === "treasury.fx_trend") {
    const points = (display.points as Array<Record<string, unknown>> | undefined) ?? [];
    if (display.empty || points.length === 0) {
      return (
        <WidgetChrome widget={widget} onExplain={onExplain}>
          <EmptyState message={String(display.message ?? "Sem cotações no período.")} />
        </WidgetChrome>
      );
    }
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        <TrendLine
          data={points.map((p) => ({
            date: String(p.date).slice(5),
            rate: Number.parseFloat(String(p.rate)) || 0,
          }))}
          xKey="date"
          yKey="rate"
          yLabel="EUR/BRL"
        />
      </WidgetChrome>
    );
  }

  if (widget.kind === "commercial" || widget.widget_id === "commercial.availability") {
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        <CommercialBody initial={display} />
      </WidgetChrome>
    );
  }

  if (widget.kind === "exceptions" || widget.widget_id === "control.exceptions") {
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        <ExceptionsBody display={display} onSeeAll={onSeeAll ? () => onSeeAll(widget) : undefined} />
      </WidgetChrome>
    );
  }

  if (widget.widget_id === "treasury.fx_exposure") {
    if (display.empty) {
      return (
        <WidgetChrome widget={widget} onExplain={onExplain}>
          <EmptyState message={String(display.message ?? "Sem saldo em moeda estrangeira.")} />
        </WidgetChrome>
      );
    }
    const quote = (display.quote as Record<string, unknown> | undefined) ?? undefined;
    const eur = (display.eur as Record<string, unknown> | undefined) ?? undefined;
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        {display.hero_brl ? (
          <p className="dash-hero">
            <MoneyDisplay amount={String(display.hero_brl)} currency="BRL" compact={compactMoney} />
          </p>
        ) : display.message ? (
          <EmptyState message={String(display.message)} />
        ) : null}
        {eur ? (
          <p>
            Aberto{" "}
            <MoneyDisplay amount={String(eur.open_balance)} currency="EUR" compact={compactMoney} />
          </p>
        ) : null}
        {display.shock_1pct_brl ? (
          <p className="muted">
            Se o euro subir 1%, ~
            <MoneyDisplay amount={String(display.shock_1pct_brl)} currency="BRL" compact={compactMoney} />
          </p>
        ) : null}
        {quote ? (
          <p className="muted">
            {formatRate(String(quote.rate_surface ?? quote.rate), 2)} BRL por euro
            {quote.stale ? " · desatualizada" : ""}
          </p>
        ) : null}
      </WidgetChrome>
    );
  }

  if (widget.widget_id === "goods.flow") {
    const segments = (display.segments as Array<Record<string, unknown>> | undefined) ?? [];
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        <FlowSteps
          steps={segments.map((seg) => ({
            key: String(seg.key),
            label: String(seg.label),
            value: String(seg.value ?? 0),
          }))}
        />
      </WidgetChrome>
    );
  }

  if (widget.widget_id === "orders.billing_progress") {
    const rows = (display.by_currency as Array<Record<string, unknown>> | undefined) ?? [];
    if (display.empty) {
      return (
        <WidgetChrome widget={widget} onExplain={onExplain}>
          <EmptyState message={String(display.message ?? "Nenhum pedido confirmado.")} />
        </WidgetChrome>
      );
    }
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        {rows.map((r) => (
          <dl key={String(r.currency)} className="dash-dl">
            <div>
              <dt>Confirmado ({String(r.currency)})</dt>
              <dd>
                <MoneyDisplay amount={String(r.confirmed)} currency={String(r.currency)} compact={compactMoney} />
              </dd>
            </div>
            <div>
              <dt>Faturado</dt>
              <dd>
                <MoneyDisplay amount={String(r.invoiced)} currency={String(r.currency)} compact={compactMoney} />
              </dd>
            </div>
            <div>
              <dt>A faturar</dt>
              <dd>
                <MoneyDisplay amount={String(r.to_invoice)} currency={String(r.currency)} compact={compactMoney} />
              </dd>
            </div>
          </dl>
        ))}
      </WidgetChrome>
    );
  }

  if (widget.kind === "aging_bar") {
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        <AgingBar rows={asRows(display.kpis_by_currency)} />
      </WidgetChrome>
    );
  }

  if (widget.kind === "table") {
    const rows = (display.rows as Array<Record<string, unknown>> | undefined) ?? [];
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        {rows.length === 0 ? (
          <EmptyState message="Nenhuma obrigação neste recorte." />
        ) : (
          <div className="table-wrap">
            <table className="operational-table">
              <thead>
                <tr>
                  <th>Vencimento</th>
                  <th>Obrigação</th>
                  <th>Saldo</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={String(r.id)}>
                    <td>{formatRelativeDue(String(r.due_date ?? ""), Number(r.days_overdue) || undefined)}</td>
                    <td>
                      {String(
                        r.display_title ?? r.invoice_number ?? r.payee_display_name ?? "Obrigação sem identificação",
                      )}
                    </td>
                    <td>
                      <MoneyDisplay
                        amount={String(r.balance ?? "0")}
                        currency={String(r.currency ?? "")}
                        compact={compactMoney}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </WidgetChrome>
    );
  }

  if (widget.widget_id === "catalog.quality") {
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        <dl className="dash-dl">
          <div>
            <dt>Produtos</dt>
            <dd>{String(display.total ?? "—")}</dd>
          </div>
          <div>
            <dt>Para revisar</dt>
            <dd>{String(display.needs_review ?? "—")}</dd>
          </div>
          <div>
            <dt>Classificação</dt>
            <dd>{String(display.classification_review ?? "—")}</dd>
          </div>
          <div>
            <dt>Sem NCM</dt>
            <dd>{String(display.missing_ncm ?? "—")}</dd>
          </div>
        </dl>
      </WidgetChrome>
    );
  }

  if (widget.kind === "quote") {
    if (display.unavailable) {
      return (
        <WidgetChrome widget={widget} onExplain={onExplain}>
          <EmptyState message="Cotação indisponível" />
        </WidgetChrome>
      );
    }
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        <p>
          <MoneyDisplay amount={String(display.rate)} currency="BRL" compact={compactMoney} /> por euro
        </p>
        <p className="muted">
          Fonte {String(display.source ?? "—")}
          {display.stale ? " · desatualizada" : ""}
        </p>
      </WidgetChrome>
    );
  }

  if (widget.widget_id === "costing.operational_published") {
    if (display.absence || display.empty) {
      return (
        <WidgetChrome widget={widget} onExplain={onExplain}>
          <EmptyState message={String(display.message ?? "Nenhum custo operacional publicado")} />
        </WidgetChrome>
      );
    }
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        <p>
          <MoneyDisplay amount={String(display.included_total_brl)} currency="BRL" compact={compactMoney} />
        </p>
        <p className="muted">{String(display.published_cases)} publicados</p>
      </WidgetChrome>
    );
  }

  if (widget.kind === "absence_block") {
    const lines = (display.lines as Array<Record<string, unknown>> | undefined) ?? [];
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        <ul className="dash-situation">
          {lines.map((line) => (
            <li key={String(line.key)}>
              <strong>{String(line.label)}</strong>
              {line.absence ? <p>{String(line.message)}</p> : <p>{String(line.value ?? "")}</p>}
            </li>
          ))}
        </ul>
      </WidgetChrome>
    );
  }

  if (widget.kind === "counts" || widget.kind === "kpi_plain") {
    const byStatus = display.by_status as Record<string, number> | undefined;
    const byLoc = display.by_location_type as Array<Record<string, unknown>> | undefined;
    const families = display.families as Array<Record<string, unknown>> | undefined;
    const entity =
      widget.widget_id === "logistics.shipments"
        ? "shipment"
        : widget.widget_id === "orders.status"
          ? "order"
          : "generic";
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        {display.empty && display.message ? (
          <EmptyState message={String(display.message)} />
        ) : (
          <>
            {byStatus ? (
              <dl className="dash-dl">
                {Object.entries(byStatus).map(([k, v]) => (
                  <div key={k}>
                    <dt>{statusLabel(k, entity)}</dt>
                    <dd>{v}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
            {byLoc ? (
              <dl className="dash-dl">
                {byLoc.map((row) => (
                  <div key={String(row.location_type)}>
                    <dt>{LOCATION_LABEL[String(row.location_type)] ?? String(row.location_type)}</dt>
                    <dd>
                      {formatQuantity(String(row.qty ?? "0"))} · {String(row.sku_count ?? 0)} SKU
                    </dd>
                  </div>
                ))}
              </dl>
            ) : null}
            {families ? (
              <dl className="dash-dl">
                {families.map((f) => (
                  <div key={String(f.doc_type)}>
                    <dt>{String(f.doc_type)}</dt>
                    <dd>{String(f.count)}</dd>
                  </div>
                ))}
              </dl>
            ) : null}
            {display.residual_qty != null ? (
              <p>Quantidade residual: {formatQuantity(String(display.residual_qty))}</p>
            ) : null}
            {display.unpriced_lines != null ? (
              <p className="muted">
                Sem preço: {String(display.unpriced_lines)} · compromisso: {String(display.commitment_lines)}
              </p>
            ) : null}
            {display.total_open != null && !families ? <p>Abertos: {String(display.total_open)}</p> : null}
          </>
        )}
      </WidgetChrome>
    );
  }

  if (widget.kind === "kpi_currency") {
    const mixed = Boolean(display.mixed_currency);
    return (
      <WidgetChrome widget={widget} onExplain={onExplain}>
        {mixed ? <p className="muted">Mais de uma moeda — totais não somados.</p> : null}
        {currencyLines(display, "amount")}
      </WidgetChrome>
    );
  }

  return (
    <WidgetChrome widget={widget} onExplain={onExplain}>
      <EmptyState message="Sem apresentação para este bloco." />
    </WidgetChrome>
  );
}
