import type { ClearanceResidual } from "../inventory/inventoryApi";
import type { ReceivingRow } from "../inventory/processReceiving";
import type { RecordTopic } from "../../ui/RecordWorkHeader";

type State = Pick<RecordTopic,"state"|"result"|"tone">;
const positive = (value:string) => Number(value) > 0;
export function quantitiesByUnit(rows:ReceivingRow[], field:"released_qty"|"received_qty"|"pending_qty"):string {
  const amounts = new Map<string,number>();
  for (const row of rows) if (positive(row[field])) {
    if (!row.unit) return "Quantidade sem unidade informada";
    amounts.set(row.unit,(amounts.get(row.unit) || 0) + Number(row[field]));
  }
  return [...amounts].map(([unit,amount]) => `${new Intl.NumberFormat("pt-BR",{maximumFractionDigits:4}).format(amount)} ${unit}`).join(" · ") || "0";
}

export function releaseState(scope:ClearanceResidual[]):State {
  if (!scope.length) return {state:"Sem escopo informado",result:"Consultar alocações e liberações",tone:"empty"};
  const outstanding=scope.filter(row=>positive(row.residual_qty)),released=scope.some(row=>positive(row.nationalized_qty));
  if (!released) return {state:"Aguardando liberação",result:`${scope.length} ${scope.length===1?"linha alocada":"linhas alocadas"}`,tone:"blocked"};
  if (outstanding.length) return {state:"Liberação parcial",result:`${outstanding.length} ${outstanding.length===1?"linha ainda tem saldo":"linhas ainda têm saldo"} a liberar`,tone:"partial"};
  return {state:"Escopo alocado liberado",result:"Consultar liberações confirmadas",tone:"complete"};
}

/** Full completion needs BOTH a complete authoritative allocation scope and physical receipts.
 * Zero pending in released rows alone NEVER proves the whole process was received.
 */
export function entryState(rows:ReceivingRow[], scope:ClearanceResidual[]|null, fullScopeKnown:boolean, cancelled=false):State {
  if (cancelled) return {state:"Bloqueado",result:"Operação cancelada",tone:"blocked"};
  const released=rows.filter(row=>positive(row.released_qty)),pending=released.filter(row=>positive(row.pending_qty));
  const received=released.some(row=>positive(row.received_qty));
  if (!released.length) return {state:"Aguardando liberação",result:"Nenhum item liberado nesta fonte",tone:"blocked"};
  if (pending.some(row=>row.state==="blocked")) return {state:"Atenção",result:pending.find(row=>row.state==="blocked")!.block_reason || "Revisar origem do item",tone:"attention"};
  if (pending.length) return {state:received?"Recebimento parcial":"A receber",result:`${quantitiesByUnit(released,"received_qty")} recebidas · ${quantitiesByUnit(pending,"pending_qty")} pendentes do liberado`,tone:received?"partial":"info"};
  if (scope?.some(row=>positive(row.residual_qty))) return {state:"Parcial — resta liberar",result:`${quantitiesByUnit(released,"received_qty")} recebidas; todo o liberado até agora`,tone:"partial"};
  if (fullScopeKnown && scope?.length && scope.every(row=>Number(row.residual_qty)===0) && !rows.some(row=>row.state==="blocked")) return {state:"Escopo integral recebido",result:`${quantitiesByUnit(released,"received_qty")} recebidas · alocações conferidas`,tone:"complete"};
  return {state:"Liberado até agora recebido",result:"Conclusão integral ainda não comprovada",tone:"info"};
}
