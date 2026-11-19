import type { OrderQtyRow } from "../billing/billingApi";
import type { ApQueueResponse } from "../reporting/reportingApi";
import type { RecordTopic } from "../../ui/RecordWorkHeader";
import { formatMoney } from "../../ui";
type State = Pick<RecordTopic,"state"|"result"|"tone">;
export function billingWorkState(rows:OrderQtyRow[],status:string):State & {eligible:boolean} {
  const eligible=status==="CONFIRMED" && rows.some(row=>row.billable && Number(row.available_qty)>0);
  const issued=rows.filter(row=>Number(row.issued_qty)>0),complete=rows.length>0 && rows.every(row=>Number(row.ordered_qty)>0 && row.billable && Number(row.issued_qty)>=Number(row.ordered_qty));
  if (complete) return {eligible,state:"Faturamento completo",result:`${rows.length} ${rows.length===1?"linha integralmente faturada":"linhas integralmente faturadas"}`,tone:"complete"};
  if (issued.length) return {eligible,state:"Faturamento parcial",result:`${issued.length} ${issued.length===1?"linha com faturamento":"linhas com faturamento"}`,tone:"partial"};
  if (eligible) {const count=rows.filter(row=>row.billable && Number(row.available_qty)>0).length;return {eligible,state:"Itens disponíveis",result:`${count} ${count===1?"linha elegível":"linhas elegíveis"} para faturar`,tone:"info"};}
  if (status==="DRAFT") return {eligible,state:"Aguardando confirmação",result:"Consultar os itens do pedido",tone:"blocked"};
  if (rows.some(row=>!row.billable)) return {eligible,state:"Vincular produto",result:"Há linhas sem elegibilidade para faturar",tone:"blocked"};
  return {eligible,state:"Sem faturamento informado",result:"Consultar faturas e quantidades",tone:"info"};
}
export function accountsWorkState(data:ApQueueResponse):State & {overdue:boolean} {
  const groups=data.kpis.kpis_by_currency || [], overdue=groups.some(group=>group.overdue_count>0);
  const open=groups.filter(group=>Number(group.open_balance)>0);
  const result=open.length>2?`${open.length} moedas com saldo aberto`:open.map(group=>formatMoney(group.open_balance,group.currency)).join(" · ");
  if (overdue) return {overdue,state:"Contas vencidas",result:result || "Consultar vencimentos",tone:"attention"};
  if (open.length) return {overdue,state:"Contas em aberto",result,tone:"info"};
  if (groups.some(group=>group.total_count>0)) return {overdue,state:"Contas quitadas",result:"Saldo das obrigações zerado",tone:"complete"};
  return {overdue,state:"Sem contas no recorte",result:"Consultar obrigações do pedido",tone:"empty"};
}
