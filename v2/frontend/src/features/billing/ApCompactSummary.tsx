import {formatMoney} from '../../ui';
type Currency={currency:string;open_balance?:string|null;overdue_balance?:string|null;due_today_balance?:string|null;next_7d_balance?:string|null};
type Credit={currency:string;unallocated_candidates_total?:string|null};
const value=(n:string|null|undefined,c:string)=>n==null?'—':formatMoney(n,c);
export function ApCompactSummary({currencies,credits,onOpen,onDue,onCredit}:{currencies:Currency[];credits:Credit[];onOpen:(c:string)=>void;onDue:(preset:'overdue'|'today'|'next7',c:string)=>void;onCredit:()=>void}){
 const all=[...new Set([...currencies.map(c=>c.currency),...credits.map(c=>c.currency)])];
 return <section className="ap-summary" aria-label="Resumo por moeda"><div className="ap-summary-heading"><span>Moeda</span><span>Saldo aberto</span><span>Vencido</span><span>Hoje</span><span>Próximos 7 dias</span><span>Por alocar <small>· fila completa</small></span></div>{all.map(currency=>{
  const c=currencies.find(x=>x.currency===currency),credit=credits.find(x=>x.currency===currency);
  return <div className="ap-summary-row" key={currency}><strong>{currency}</strong>
   <button aria-label={`Saldo aberto ${currency}`} data-testid={`kpi-open-balance-${currency}`} onClick={()=>onOpen(currency)}>{value(c?.open_balance,currency)}</button>
   <button aria-label={`Vencido ${currency}`} data-testid={`kpi-overdue-${currency}`} onClick={()=>onDue('overdue',currency)}>{value(c?.overdue_balance,currency)}</button>
   <button aria-label={`Hoje ${currency}`} data-testid={`kpi-today-${currency}`} onClick={()=>onDue('today',currency)}>{value(c?.due_today_balance,currency)}</button>
   <button aria-label={`Próximos 7 dias ${currency}`} data-testid={`kpi-next7-${currency}`} onClick={()=>onDue('next7',currency)}>{value(c?.next_7d_balance,currency)}</button>
   <button aria-label={`Pagamentos por alocar ${currency} — abrir fila completa`} data-testid={`kpi-unallocated-${currency}`} onClick={onCredit}>{credit?value(credit.unallocated_candidates_total,currency):'—'}</button>
  </div>;
 })}{!all.length&&<p>Nenhum saldo por moeda informado.</p>}<details className="ap-summary-help"><summary>Sobre os valores</summary><p>Obrigações conforme os filtros, sem somar moedas. Pagamentos por alocar abrem a fila completa: registrar um pagamento não reduz a obrigação até sua alocação.</p></details></section>;
}
