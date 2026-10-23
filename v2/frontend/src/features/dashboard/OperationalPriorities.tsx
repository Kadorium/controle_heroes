import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchDashboard, type DashboardWidget } from "./dashboardApi";
import { hasFailure, incomplete, moduleLabel, rows, severityLabel, text } from "./executiveDisplay";

export function OperationalPriorities({ refreshKey }: { refreshKey: number }) {
  const [widget, setWidget] = useState<DashboardWidget | null>(null);
  const [busy, setBusy] = useState(true), [error, setError] = useState(false), [retry, setRetry] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setBusy(true); setError(false); setWidget(null);
    // One existing public snapshot; ACL, ordering, severity and href remain owned by Reporting.
    void fetchDashboard({ view: "controle" }, controller.signal).then(snapshot => {
      if (!controller.signal.aborted) setWidget(snapshot.widgets.find(w => w.widget_id === "control.exceptions" && w.status === "AVAILABLE") ?? null);
    }).catch(() => { if (!controller.signal.aborted) setError(true); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, [refreshKey, retry]);
  const d = widget?.display ?? {}, items = rows(d.items), partial = incomplete(d);
  return <section className="exec-priorities" data-testid="executive-priorities" data-demo-control-state={busy ? "loading" : error ? "error" : "settled"}>
    <div className="exec-section-heading"><h2>Próxima ação operacional</h2><Link to="/dashboard?view=controle">Ver exceções →</Link></div>
    {busy ? <p role="status">Consultando prioridades…</p> : error || (widget && hasFailure(widget)) ?
      <div role="status" className="exec-local-warning">Não foi possível consultar as prioridades. <button type="button" className="btn-ghost" onClick={() => setRetry(n => n + 1)}>Tentar novamente</button></div> : !widget ?
      <p className="muted">Prioridades indisponíveis para este acesso.</p> : <>
      {partial && <p className="exec-local-warning">Consulta parcial: algumas áreas estão indisponíveis. As exceções recebidas permanecem visíveis.</p>}
      {items.length ? <>
        <article className="exec-priority">
          <span className={`exec-severity exec-severity--${text(items[0].severity)}`}>{severityLabel[text(items[0].severity)] ?? text(items[0].severity)} · {moduleLabel[text(items[0].module)] ?? text(items[0].module)}</span>
          <h3>{text(items[0].title)}</h3><p>{text(items[0].reason)}</p>
          <div className="exec-priority-footer"><span>{text(d.total_count)} exceção(ões) consultada(s)</span>{items[0].href ? <Link className="ui-button" to={String(items[0].href)}>Consultar origem →</Link> : <span>Origem sem link disponível</span>}</div>
        </article>
        {items.length > 1 && <details className="exec-details"><summary>Outras prioridades</summary><ul>{items.slice(1, 5).map((item, n) => <li key={n}><strong>{severityLabel[text(item.severity)] ?? text(item.severity)}</strong> · {item.href ? <Link to={String(item.href)}>{text(item.title)}</Link> : text(item.title)} — {text(item.reason)}</li>)}</ul><Link to="/dashboard?view=controle">Abrir lista completa</Link></details>}
      </> : d.total_count === 0 && !partial && ["ok", "empty"].includes(text(d.state)) ? <p>Nenhuma exceção nas áreas consultadas.</p> : <p>Não foi possível concluir se há exceções em todas as áreas consultadas.</p>}
    </>}
  </section>;
}
