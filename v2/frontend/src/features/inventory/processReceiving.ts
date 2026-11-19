import { useEffect, useState } from "react";
import type { components } from "../../api/generated/schema";
export type ReceivingRow = components["schemas"]["ReceivingRow"];
export type ReceivingPageData = components["schemas"]["ReceivingPage"];

/** The existing API has item_id but no process filter. Read ALL pages before exact ID selection.
 * Never use text coincidence or a single page as proof of a process scope.
 * The global queue keeps server pagination; this collection is only used for a selected process.
 */
export async function readProcessReceiving(processId: number, signal?: AbortSignal): Promise<ReceivingRow[]> {
  if (!Number.isSafeInteger(processId) || processId <= 0) throw new Error("Operação inválida.");
  const all = new Map<number, ReceivingRow>(); let total: number | null = null;
  for (let offset = 0; ; offset += 100) {
    const response = await fetch(`/api/inventory/receiving?state=all&limit=100&offset=${offset}`, { credentials: "include", signal });
    if (!response.ok) throw new Error(response.status === 403 ? "Seu acesso não permite consultar a entrada no estoque." : "Não foi possível consultar todas as mercadorias. Tente novamente.");
    const page = await response.json() as ReceivingPageData;
    if (!Number.isSafeInteger(page.total) || page.total < 0 || page.total > 10000) throw new Error("A fila excede o limite da consulta contextual. Use a fila global; o recorte desta operação não foi carregado.");
    if (total !== null && page.total !== total) throw new Error("A fila mudou durante a consulta. Atualize para obter o recorte completo.");
    total = page.total;
    for (const row of page.rows) all.set(row.item_id, row);
    if (offset + page.rows.length >= total) break;
    if (page.rows.length !== 100) throw new Error("Consulta incompleta. Atualize antes de receber mercadorias.");
  }
  if (all.size !== total) throw new Error("A fila mudou durante a consulta. Atualize para obter o recorte completo.");
  return [...all.values()].filter(row => row.process_id === processId);
}

export function useProcessReceiving(processId: number | null, refresh = 0) {
  const [tick, setTick] = useState(0);
  const [state, setState] = useState<{ id:number|null; data:ReceivingRow[]|null; error:string|null; busy:boolean }>({id:null,data:null,error:null,busy:false});
  useEffect(() => {
    const controller = new AbortController();
    setState({id:processId,data:null,error:null,busy:processId !== null});
    if (processId !== null) void readProcessReceiving(processId,controller.signal)
      .then(data => { if (!controller.signal.aborted) setState({id:processId,data,error:null,busy:false}); })
      .catch(error => { if (!controller.signal.aborted) setState({id:processId,data:null,error:error.message,busy:false}); });
    return () => controller.abort();
  }, [processId, refresh, tick]);
  return { ...(state.id === processId ? state : {data:null,error:null,busy:processId !== null}), retry:() => setTick(value => value + 1) };
}
