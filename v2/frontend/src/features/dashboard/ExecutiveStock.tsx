import { Link } from "react-router-dom";
import { number, useRead, type StockPosition } from "../inventory/stockRead";
export function ExecutiveStock({refreshKey}:{refreshKey:number}) {
  const read=useRead<StockPosition>(`/api/reporting/stock-positions?limit=1&status=positive&refresh=${refreshKey}`);
  return <section className="exec-kpi" data-testid="executive-stock"><h2>Estoque atual</h2>
    {read.busy?<p role="status">Consultando estoque…</p>:read.error?<p role="status">Estoque indisponível. <button className="btn-ghost" onClick={read.retry}>Tentar novamente</button></p>:read.data?<>
      <div className="exec-stock-value">{read.data.total} <small>{read.data.total===1?"produto com saldo":"produtos com saldo"}</small></div>
      {read.data.totals.map(t=><p className="exec-caption" key={t.unit||"?"}>{t.unit?`${number(t.quantities.DOMESTIC)} ${t.unit} disponíveis`:`${t.sku_count} ${t.sku_count===1?"produto sem unidade cadastrada":"produtos sem unidade cadastrada"} · quantidades no detalhe`}</p>)}
      <p className="exec-caption">Posição física atual · saldos por regime</p></>:null}
    <Link className="exec-drill" to="/inventory/positions">Consultar estoque →</Link>
  </section>;
}
