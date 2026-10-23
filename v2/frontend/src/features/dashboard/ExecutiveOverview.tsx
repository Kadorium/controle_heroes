import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { MoneyDisplay, TrendLine } from "../../ui";
import { formatDateOnly, formatMoney, formatRate } from "../../ui/format";
import {formatDateTime} from './localDateTime';
import type { DashboardSnapshot, DashboardWidget } from "./dashboardApi";
import { amount, fields, hasFailure, incomplete, monthRange, rows, text } from "./executiveDisplay";
import { OperationalPriorities } from "./OperationalPriorities";
import { ExecutiveStock } from "./ExecutiveStock";
import type { User } from "../auth/types";
import "./executive.css";

function Money({ value, currency }: { value: unknown; currency: unknown }) {
  const v = amount(value), code = text(currency, "");
  if (v == null) return <span title="Valor não informado">{code ? `${code} —` : "—"}</span>;
  return <span title={formatMoney(v, code)}><MoneyDisplay amount={v} currency={code} compact={v != null && Math.abs(Number(v)) >= 1_000_000} /></span>;
}
function Block({ widget, title, caption, summary, onExplain, children }: { widget: DashboardWidget; title: string; caption?: string; summary?: boolean; onExplain: (w: DashboardWidget) => void; children: ReactNode }) {
  return <section className={summary ? "exec-kpi" : "exec-block"} data-testid={`dash-widget-${widget.widget_id}`}>
    <div className="exec-section-heading"><h2>{title}</h2><button type="button" className="dash-tip" aria-label={`O que é ${title}`} onClick={() => onExplain({ ...widget, label: title })}>ⓘ</button></div>
    {hasFailure(widget) ? <p role="status">Informação indisponível. Use Atualizar para tentar novamente.</p> : children}
    {caption && <p className="exec-caption">{caption}</p>}
    {widget.drill && <Link className="exec-drill" to={widget.drill}>{widget.widget_id === "ap.overdue" ? "Abrir fila de vencidas" : "Abrir fila completa"} →</Link>}
  </section>;
}
const operationNames: Record<string, string> = { confirmed: "pedidos confirmados", to_invoice: "linhas a faturar", shipments: "embarques em curso", customs: "processos na aduana", stock: "SKUs com saldo em estoque" };

export function ExecutiveOverview({ snapshot, refreshKey, onExplain, onSeeAll, canInventory = false, user }: { snapshot: DashboardSnapshot; refreshKey: number; onExplain: (w: DashboardWidget) => void; onSeeAll: (w: DashboardWidget) => void; canInventory?: boolean; user?:User }) {
  const widgets = snapshot.widgets.filter(w => w.status === "AVAILABLE");
  const get = (id: string) => widgets.find(w => w.widget_id === id);
  const cash = get("ap.cash_committed"), flow = get("goods.flow"), inbox = get("attention.inbox"), trend = get("treasury.fx_trend"), progress = get("orders.billing_progress");
  const labels = fields(cash?.display.labels), range = monthRange(cash?.display ?? {});
  const kpis = ["treasury.fx_exposure", ...(!canInventory ? ["ap.cash_due", "ap.overdue", "orders.to_invoice"] : [])].map(get).filter((w): w is DashboardWidget => !!w);
  return <div className="executive-overview">
    <div className={`exec-summary ${canInventory ? "exec-summary--experience" : ""}`} data-demo-summary data-testid="executive-summary">
      {kpis.map(w => {
        const d = w.display, quote = fields(d.quote), currencies = rows(d.by_currency);
        const fx = w.widget_id === "treasury.fx_exposure";
        const title = fx ? "Exposição em EUR · referência BRL" : w.widget_id === "ap.cash_due" ? `Compromissos · ${range}` : w.widget_id === "ap.overdue" ? "Obrigações vencidas" : w.label;
        return <Block key={w.widget_id} widget={w} title={title} summary onExplain={onExplain} caption={w.widget_id === "orders.to_invoice" ? "Pedidos confirmados · posição atual" : w.widget_id === "ap.cash_due" ? "Saldo nos meses civis indicados" : undefined}>
          {fx ? <>
            <div className="exec-value">{d.hero_brl != null && quote.rate != null ? <Money value={d.hero_brl} currency="BRL" /> : <span className="exec-word">{d.empty === true ? "Sem saldo estrangeiro" : quote.rate == null ? "Cotação indisponível" : "Equivalente indisponível"}</span>}</div>
            <p className="exec-caption">{rows(d.foreign).map((r, n) => <span key={n}><Money value={r.open_balance} currency={r.currency} />{n < rows(d.foreign).length - 1 ? " · " : ""}</span>)}{d.empty !== true && <span> · {quote.rate == null ? "sem equivalente" : quote.stale ? "cotação desatualizada" : "cotação de referência"}</span>}</p>
            {quote.rate != null && <p className="exec-caption">{formatRate(amount(quote.rate_full ?? quote.rate), 4)} · {text(quote.source)} · {formatDateTime(text(quote.observed_at))}</p>}
            {rows(d.foreign).some(r=>r.currency!=="EUR") && <p className="exec-caption">{rows(d.foreign).filter(r=>r.currency!=="EUR").map(r=>text(r.currency)).join(", ")}: sem conversão neste indicador. O equivalente em reais cobre somente EUR.</p>}
          </> : w.widget_id === "ap.overdue" && d.total_count === 0 && d.overdue_count === 0 && d.state === "ok" ? <><div className="exec-value exec-word">Nenhuma</div><p className="exec-caption">Nenhuma obrigação vencida no recorte consultado.</p></> : currencies.length ? currencies.map((r, n) => <div className="exec-value" key={n}><Money value={r.amount} currency={r.currency} /></div>) : <p>{d.empty === true && d.message ? text(d.message) : "Valores não disponíveis"}</p>}
        </Block>;
      })}
      {canInventory && <OperationalPriorities refreshKey={refreshKey} />}
    </div>
    {canInventory && user && <ExecutiveStock refreshKey={refreshKey} user={user} />}
    <div className="exec-primary">
      <div>{!canInventory && <OperationalPriorities refreshKey={refreshKey} />}
        {inbox && <details className="exec-details" data-testid="executive-financial-priorities"><summary>Pendências financeiras e de cadastro</summary>
          {hasFailure(inbox) || incomplete(inbox.display) ? <p>Consulta incompleta. Algumas pendências podem não estar disponíveis.</p> : null}
          {rows(inbox.display.items).length ? <ul>{rows(inbox.display.items).map((it, n) => <li key={n}>{it.href ? <Link to={String(it.href)}>{text(it.title)}</Link> : text(it.title)} — {text(it.reason)}</li>)}</ul> : !hasFailure(inbox) && !incomplete(inbox.display) && inbox.display.total_count === 0 ? <p>Nenhuma pendência financeira ou de cadastro apontada neste recorte consultado.</p> : <p>Sem conclusão disponível para este recorte.</p>}
          {Number(inbox.display.total_count) > rows(inbox.display.items).length && <button className="btn-ghost" onClick={() => onSeeAll(inbox)}>Ver todas as pendências consultadas</button>}
        </details>}
      </div>
      <div>{canInventory && ["ap.cash_due","ap.overdue"].map(get).filter((w):w is DashboardWidget=>!!w).map(w=><div className="exec-due-line" key={w.widget_id}><Block widget={w} title={w.widget_id==="ap.cash_due"?`Vencimentos · ${range}`:"Vencidos no recorte"} onExplain={onExplain}>{rows(w.display.by_currency).length ? rows(w.display.by_currency).map((r,n)=><div className="exec-due-value" key={n}><Money value={r.amount} currency={r.currency}/></div>):<p>{w.display.state==="ok" && w.display.total_count===0 && w.display.overdue_count===0?"Nenhuma obrigação vencida no recorte.":w.display.empty===true?"Nenhum compromisso no recorte.":"Valores não disponíveis."}</p>}</Block></div>)}
      {flow && <details className="exec-details" data-testid="dash-widget-goods.flow"><summary>Posição atual da operação</summary><section><div className="exec-section-heading"><h2>Posição atual da operação</h2><button className="dash-tip" aria-label="Sobre a posição atual" onClick={() => onExplain(flow)}>ⓘ</button></div>
        {hasFailure(flow) ? <p>Posição operacional indisponível.</p> : rows(flow.display.segments).length === 0 ? <p>Nenhuma posição disponível para o seu acesso neste recorte.</p> : <ul className="exec-operations">{rows(flow.display.segments).map((seg, n) => <li key={n}><span><strong>{text(seg.value)}</strong> {operationNames[text(seg.key)] ?? text(seg.label)}</span>{seg.href ? <Link to={String(seg.href)} aria-label={`Consultar ${operationNames[text(seg.key)] ?? text(seg.label)}`}>Consultar →</Link> : null}</li>)}</ul>}
        <p className="exec-caption">Chegada, nacionalização e recebimento são marcos distintos.</p>
      </section></details>}</div>
    </div>
    <div className="exec-complementary">
      {cash && <Block widget={cash} title="Agenda de caixa" caption={`Meses civis · ${range}${cash.display.as_of_month ? ` · base ${formatDateOnly(String(cash.display.as_of_month))}` : ""}`} onExplain={onExplain}>
        {rows(cash.display.by_currency).length ? rows(cash.display.by_currency).map((r, n) => <div key={n}><h3>{text(r.currency)}</h3><dl className="exec-agenda">{["overdue", "m0", "m1", "m2"].map(k => <div key={k}><dt>{k === "overdue" ? `Antes de ${text(labels.m0, "este mês")}` : text(labels[k])}</dt><dd><Money value={fields(r.buckets)[k]} currency={r.currency} /></dd>{fields(r.counts)[k] != null && <small>{text(fields(r.counts)[k])} {Number(fields(r.counts)[k])===1?"obrigação":"obrigações"}</small>}</div>)}</dl></div>) : <p>{cash.display.empty === true ? "Nenhum compromisso nos meses consultados." : "Agenda indisponível."}</p>}
        <details className="exec-details"><summary>Escopo da agenda</summary><p>Meses civis retornados pela consulta, mais vencimentos anteriores ao primeiro mês. O primeiro mês inclui vencimentos anteriores a hoje. O limite Até restringe os compromissos; não representa uma projeção diária de 90 dias. O limite De não é aplicado a esta agenda.</p></details>
      </Block>}
      {trend && <Block widget={trend} title="Referência cambial" caption={`Histórico observado · últimos ${text(trend.display.days)} dias`} onExplain={onExplain}>
        {rows(trend.display.points).length === 0 ? <p>Sem cotações na série consultada.</p> : rows(trend.display.points).length === 1 ? (() => { const p = rows(trend.display.points)[0]; return <><div className="exec-rate">{formatRate(amount(p.rate), 6)} <small>{text(trend.display.base)} por {text(trend.display.foreign)}</small></div><p className="exec-caption">{formatDateOnly(text(p.date))} · {text(p.source)}</p><p className="exec-caption">Um dia observado. Série insuficiente para indicar tendência.</p></>; })() : <TrendLine data={rows(trend.display.points).map(p => ({ date: formatDateOnly(text(p.date)), rate: amount(p.rate) == null ? NaN : Number(p.rate) }))} xKey="date" yKey="rate" yLabel={`${text(trend.display.foreign)}/${text(trend.display.base)}`} height={160} />}
        {get("treasury.fx_exposure") && <details className="exec-details"><summary>Cotação usada no equivalente</summary>{(() => { const d = get("treasury.fx_exposure")!.display, q = fields(d.quote); return <><p>{q.rate == null ? "Cotação indisponível." : `${formatRate(amount(q.rate_full ?? q.rate), 6)} · ${text(q.source)} · ${formatDateTime(text(q.observed_at))}${q.stale ? " · desatualizada" : ""}`}</p><p>Equivalente de referência, não câmbio bancário realizado.</p>{d.shock_1pct_brl != null && <p>Alta de 1%: <Money value={d.shock_1pct_brl} currency="BRL" /> de sensibilidade, conforme cálculo retornado.</p>}</>; })()}</details>}
      </Block>}
    </div>
    {progress && <Block widget={progress} title="Pedidos e faturamento" caption="Posição atual dos pedidos confirmados · faturado não significa quitado" onExplain={onExplain}>
      {rows(progress.display.by_currency).length ? rows(progress.display.by_currency).map((r, n) => <dl className="exec-billing" key={n}>{[["Confirmado", "confirmed"], ["Faturado", "invoiced"], ["A faturar", "to_invoice"]].map(([label, key]) => <div key={key}><dt>{label}</dt><dd><Money value={r[key]} currency={r.currency} /></dd></div>)}</dl>) : <p>{progress.display.empty === true ? "Nenhum pedido confirmado neste recorte." : "Valores indisponíveis."}</p>}
    </Block>}
  </div>;
}
