import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import type { components } from "../../api/generated/schema";
import type { User } from "../auth/types";
import { canReadInventory, canWriteInventory } from "./inventoryPermissions";
import { useRead, number } from "./stockRead";
import type { StockLocation } from "./inventoryApi";
import { useProcessReceiving, type ReceivingPageData, type ReceivingRow } from "./processReceiving";
import { contextReturn } from "../../navigation/contextReturn";
import "./receiving.css";

type Command = components["schemas"]["ReceiveIn"];
type Result = components["schemas"]["ReceiveResult"];
type Pending = { body:Command; label:string; destination:string };
const labels = { pending:"A receber", complete:"Liberado recebido", blocked:"Bloqueado" };
const canCustoms = (user:User) => user.role === "admin" || user.permissions.includes("customs:read");

export function ReceivingPage({ user }:{ user:User }) {
  const [params,setParams] = useSearchParams();
  const allowed = canReadInventory(user), writable = canWriteInventory(user);
  const scoped = params.has("process_id"), processId = Number(params.get("process_id"));
  const validProcess = Number.isSafeInteger(processId) && processId > 0;
  const itemId = Number(params.get("item")) || 0, q = params.get("q") || "", state = params.get("state") || (scoped ? "all" : "pending");
  const offset = Math.max(0,Number(params.get("offset")) || 0);
  const key = `epic.receiving.pending:${user.id}`;
  const [pending,setPending] = useState<Pending|null>(() => { try { return JSON.parse(sessionStorage.getItem(key) || "null"); } catch { return null; } });
  const sourceId = pending?.body.item_id || itemId;
  const globalQueue = useRead<ReceivingPageData>(allowed && !scoped ? `/api/inventory/receiving?q=${encodeURIComponent(q)}&state=${state}&offset=${offset}` : null);
  const processRows = useProcessReceiving(allowed && scoped && validProcess ? processId : null);
  const selectedRows = processRows.data?.filter(row => (state === "all" || row.state === state) && (!q || [row.sku,row.product_name,row.process_code,row.process_reference,row.release_reference].join(" ").toLocaleLowerCase().includes(q.toLocaleLowerCase()))) ?? null;
  const queue = scoped ? { ...processRows, data:selectedRows ? {rows:selectedRows.slice(offset,offset+25),total:selectedRows.length,limit:25,offset} : null } : globalQueue;
  const detail = useRead<ReceivingPageData>(allowed && sourceId ? `/api/inventory/receiving?item_id=${sourceId}&state=all` : null);
  const places = useRead<StockLocation[]>(allowed && writable && sourceId ? "/api/inventory/locations" : null);
  const source = detail.data?.rows[0];
  const mismatch = !!source && scoped && source.process_id !== processId;
  const row = mismatch ? undefined : source;
  const destinations = places.data?.filter(place => place.active && place.location_type === "DOMESTIC") || [];
  const [quantity,setQuantity] = useState(""), [destination,setDestination] = useState("DOMESTIC-MAIN");
  const [error,setError] = useState(""), [busy,setBusy] = useState(false), [uncertain,setUncertain] = useState(!!pending), [result,setResult] = useState<Result|null>(null);
  const flight = useRef(false), heading = useRef<HTMLHeadingElement>(null), reviewHeading = useRef<HTMLHeadingElement>(null), lastItem = useRef(0), initialized = useRef(0);
  const qty = Number(quantity.replace(",","."));
  const invalid = !!row && (!Number.isFinite(qty) || qty <= 0 || qty > Number(row.pending_qty) || !/^\d{1,14}([.,]\d{1,4})?$/.test(quantity));
  const origin = contextReturn(params.get("return_to"));
  const returnTo = origin && (!origin.startsWith("/customs/") || canCustoms(user)) ? origin : null;
  const reference = row || processRows.data?.[0];

  function patch(values:Record<string,string|null>) {
    const next = new URLSearchParams(params);
    Object.entries(values).forEach(([key,value]) => value === null ? next.delete(key) : next.set(key,value));setParams(next);
  }
  useEffect(()=>{if(pending && itemId!==pending.body.item_id)patch({item:String(pending.body.item_id)});},[pending?.body.item_id]);
  function back() { if (busy || uncertain) return;lastItem.current=itemId;setPending(null);setError("");setResult(null);patch({item:null}); }
  useEffect(() => { if (row && initialized.current !== row.item_id) { initialized.current=row.item_id;setQuantity(row.pending_qty);setError("");heading.current?.focus(); } },[row]);
  useEffect(() => { if (!itemId && !pending) { initialized.current=0;if(lastItem.current && queue.data){(document.getElementById(`receive-open-${lastItem.current}`) || heading.current)?.focus();lastItem.current=0;} } },[itemId,queue.data,pending]);
  useEffect(() => { if (destinations.length && !destinations.some(place => place.code === destination)) setDestination(destinations[0].code); },[places.data]);
  useEffect(() => {
    const onKey = (event:KeyboardEvent) => { if (event.key === "Escape" && sourceId && !busy && !uncertain) { event.preventDefault();if(pending){setPending(null);requestAnimationFrame(() => document.getElementById("receipt-quantity")?.focus());}else back(); } };
    window.addEventListener("keydown",onKey);return () => window.removeEventListener("keydown",onKey);
  });
  function review(value:ReceivingRow) {
    if (!writable || invalid || !value.unit || value.state !== "pending" || !destinations.some(place => place.code === destination)) return;
    setError("");setResult(null);setPending({body:{item_id:value.item_id,quantity:quantity.replace(",","."),unit:value.unit,location_code:destination,request_key:crypto.randomUUID()},label:value.product_name || value.sku || "Produto",destination:destinations.find(place => place.code === destination)!.name});
    requestAnimationFrame(() => reviewHeading.current?.focus());
  }
  async function confirm() {
    if (!pending || flight.current || !writable || !row || row.item_id !== pending.body.item_id || (scoped && row.process_id !== processId)) return;
    flight.current=true;setBusy(true);setError("");sessionStorage.setItem(key,JSON.stringify(pending));setUncertain(true);
    try {
      const response = await fetch("/api/inventory/receiving/confirm",{method:"POST",credentials:"include",headers:{"Content-Type":"application/json"},body:JSON.stringify(pending.body)});
      if (!response.ok) { const problem=await response.json().catch(() => null);if(response.status<500){sessionStorage.removeItem(key);setUncertain(false);}throw new Error(typeof problem?.message === "string" ? problem.message : "Não foi possível confirmar. Tente novamente."); }
      const value = await response.json() as Result;setResult(value);sessionStorage.removeItem(key);setPending(null);setUncertain(false);
      setQuantity(String(Math.max(0,Number(row.pending_qty)-Number(value.quantity))));if(!itemId)patch({item:String(pending.body.item_id)});queue.retry();detail.retry();
      requestAnimationFrame(() => document.getElementById("receipt-result")?.focus());
    } catch (error) { setError(error instanceof TypeError ? "Resposta não recebida. Tente confirmar novamente; a operação não será duplicada." : (error as Error).message); }
    finally { flight.current=false;setBusy(false); }
  }
  if (!allowed) return <section><h1>Mercadorias a receber</h1><p role="alert">Seu acesso não permite consultar recebimentos.</p></section>;
  if (scoped && !validProcess) return <section><h1>Mercadorias a receber</h1><p role="alert">Operação inválida. Nenhuma consulta ampla foi aberta.</p><Link to="/inventory/receiving">Voltar à fila global</Link></section>;
  const feedback = (value:{busy:boolean;error:string|null;retry:()=>void}) => value.busy ? <p role="status">Carregando…</p> : value.error ? <p role="alert">{value.error} <button onClick={value.retry}>Tentar novamente</button></p> : null;
  const groups = new Map<number,ReceivingRow[]>();for (const entry of queue.data?.rows || []) groups.set(entry.process_id,[...(groups.get(entry.process_id) || []),entry]);
  const scopeHref = (entry:ReceivingRow) => { const query=new URLSearchParams({process_id:String(entry.process_id),state:"all",return_to:"/inventory/receiving"+(params.size?`?${params}`:"")});return `/inventory/receiving?${query}`; };
  return <section className="receiving-page" data-testid="receiving-page">
    <header><div><div className="page-title-row"><h1 ref={heading} tabIndex={-1}>{sourceId ? "Receber mercadorias" : "Mercadorias a receber"}</h1></div>
      {scoped && <p className="receiving-origin" data-testid="receiving-scope">Operação {reference?.process_code || `#${processId}`} {reference?.process_reference ? `· ${reference.process_reference}` : ""}</p>}</div>
      <div>{sourceId>0 && <button disabled={busy||uncertain} onClick={back}>← Voltar aos itens</button>}{returnTo && <Link to={returnTo}>{returnTo.startsWith("/customs/") ? "Voltar à operação" : "Voltar à fila global"}</Link>}{!returnTo && scoped && <Link to="/inventory/receiving">Fila global</Link>}<Link to="/inventory/positions">Estoque atual</Link></div>
    </header>
    {error && <p className="receiving-error" role="alert">{error}</p>}
    {result && <div className="receiving-result" id="receipt-result" tabIndex={-1} role="status"><strong>Entrada #{result.receipt_id} {result.status === "CONFIRMED" ? "confirmada" : "revertida"} · {number(result.quantity)} {row?.unit}</strong><span>{new Date(result.received_at!).toLocaleString("pt-BR")} · {result.location_code}</span><div><Link to={`/inventory/sku/${result.product_id}`}>Ver saldo</Link><Link to={`/inventory/movements?product_id=${result.product_id}`}>Ver histórico</Link>{returnTo?.startsWith("/customs/") && <Link to={returnTo}>Consultar operação atualizada</Link>}</div></div>}
    {mismatch ? <p role="alert">Este item não pertence à operação selecionada. Nenhuma entrada pode ser confirmada neste contexto. {pending && <Link to={`/inventory/receiving?item=${pending.body.item_id}&state=all`}>Reabrir a confirmação no item correto</Link>}</p> : pending ? <section className="receiving-review">
      <h2 ref={reviewHeading} tabIndex={-1}>Conferir entrada</h2>{feedback(detail)}<p>{row?.process_code} · {row?.process_reference} · {row?.release_reference}</p><p><strong>{pending.label}</strong></p>
      <dl><div><dt>Quantidade</dt><dd>{number(pending.body.quantity)} {pending.body.unit}</dd></div><div><dt>Destino</dt><dd>{pending.destination}</dd></div></dl>
      {uncertain && <p>Confirmação em verificação. Repetir usa a mesma operação.</p>}
      <div className="receiving-actions"><button className="receiving-primary" disabled={busy||!writable||!row} onClick={() => void confirm()}>{busy ? "Confirmando…" : "Confirmar entrada"}</button><button disabled={busy||uncertain} onClick={() => {setPending(null);setError("");requestAnimationFrame(() => document.getElementById("receipt-quantity")?.focus());}}>Alterar</button></div>
    </section> : itemId>0 ? <>
      {feedback(detail)}{row && <section className="receiving-detail"><p className="receiving-origin">{row.process_code} · {row.process_reference} · {row.release_reference || `Liberação ${row.nationalization_id}`}</p><h2>{row.product_name || row.sku || "Produto não vinculado"}</h2><p className="muted">{row.sku} · {row.unit || "Unidade não cadastrada"}</p>
        <dl className="receiving-quantities"><div><dt>Liberado</dt><dd>{number(row.released_qty)} {row.unit}</dd></div><div><dt>Já recebido</dt><dd>{number(row.received_qty)} {row.unit}</dd></div><div><dt>Pendente do liberado</dt><dd data-testid="receiving-pending">{number(row.pending_qty)} {row.unit}</dd></div></dl>
        {row.state === "blocked" ? <p role="alert">{row.block_reason}. Solicite a revisão à operação responsável.</p> : row.state === "complete" ? <p role="status">Quantidade liberada deste item totalmente recebida. Isso não comprova a conclusão de toda a operação.</p> : writable ? <form onSubmit={event => {event.preventDefault();review(row);}}>
          <div className="receiving-fields"><label htmlFor="receipt-quantity">Quantidade ({row.unit})<input id="receipt-quantity" inputMode="decimal" value={quantity} aria-invalid={invalid} aria-describedby={invalid ? "receiving-quantity-error" : undefined} onChange={event => setQuantity(event.target.value)}/></label><label>Destino<select aria-label="Destino" value={destination} onChange={event => setDestination(event.target.value)}>{destinations.map(place => <option key={place.id} value={place.code}>{place.name}</option>)}</select></label></div>
          {invalid && <p id="receiving-quantity-error" className="receiving-error">Informe uma quantidade maior que zero, até {number(row.pending_qty)} {row.unit}, com no máximo quatro casas decimais.</p>}{feedback(places)}{places.data && !destinations.length && <p role="alert">Nenhuma localização doméstica ativa. Solicite a revisão do cadastro.</p>}
          <button className="receiving-primary" type="submit" disabled={invalid||!destinations.length}>Conferir entrada</button>
        </form> : <p>Seu acesso permite consultar, mas não receber.</p>}
      </section>}{detail.data && !row && <p role="alert">Origem não encontrada.</p>}
    </> : <>
      <div className="receiving-filters"><label>Buscar<input aria-label="Buscar recebimento" placeholder={scoped ? "Produto ou SKU nesta operação" : "Produto, SKU ou operação"} value={q} onChange={event => patch({q:event.target.value,offset:null})}/></label><label>Situação<select aria-label="Situação do recebimento" value={state} onChange={event => patch({state:event.target.value,offset:null})}><option value="pending">A receber</option><option value="complete">Liberados recebidos</option><option value="blocked">Bloqueados</option><option value="all">Todos</option></select></label><button onClick={queue.retry}>Atualizar</button></div>
      {feedback(queue)}{queue.data && <><p className="muted">{queue.data.total} {queue.data.total === 1 ? "item" : "itens"} no recorte {scoped ? "desta operação" : "da fila"}. {queue.data.total>25 ? "Agrupamento por operação nesta página." : ""}</p>
        {queue.data.rows.length ? <div className="experience-table-wrap"><table className="experience-table"><thead><tr><th>Produto / liberação</th><th>Unidade</th><th className="numeric">Liberado</th><th className="numeric">Recebido</th><th className="numeric">Pendente</th><th>Situação</th><th><span className="sr-only">Ação</span></th></tr></thead><tbody>
          {[...groups.entries()].map(([groupId,entries]) => <ReceivingGroup key={groupId} rows={entries} scoped={scoped} writable={writable} scopeHref={scopeHref(entries[0])} onOpen={entry => {setResult(null);patch({item:String(entry.item_id)});}}/>)}
        </tbody></table></div> : <p>Nenhum item neste filtro. {scoped && !processRows.data?.length ? "A operação não possui itens de liberação disponíveis nesta fonte." : ""}</p>}
        {queue.data.total>25 && <div className="receiving-actions"><button disabled={!offset} onClick={() => patch({offset:String(Math.max(0,offset-25))})}>Anterior</button><span>{offset+1}–{Math.min(offset+25,queue.data.total)} de {queue.data.total}</span><button disabled={offset+25>=queue.data.total} onClick={() => patch({offset:String(offset+25)})}>Próxima</button></div>}
      </>}
    </>}
  </section>;
}

function ReceivingGroup({ rows, scoped, writable, scopeHref, onOpen }:{rows:ReceivingRow[];scoped:boolean;writable:boolean;scopeHref:string;onOpen:(row:ReceivingRow)=>void}) {
  const first=rows[0];
  return <>
    {!scoped && <tr className="receiving-group"><th colSpan={7}><div><span><strong>{first.process_code}</strong> {first.process_reference && <span>· {first.process_reference}</span>}<small>{rows.length} {rows.length===1 ? "item nesta página" : "itens nesta página"}</small></span><Link to={scopeHref}>Ver itens da operação</Link></div></th></tr>}
    {rows.map(row => <tr key={row.item_id} data-receiving-item={row.item_id} data-process-id={row.process_id}><td><strong>{row.product_name || "Produto não vinculado"}</strong><small>{row.sku} · {row.release_reference || `Liberação ${row.nationalization_id}`}</small></td><td>{row.unit || "Não cadastrada"}</td><td className="numeric">{number(row.released_qty)}</td><td className="numeric">{number(row.received_qty)}</td><td className="numeric"><strong>{number(row.pending_qty)}</strong></td><td>{row.block_reason || (Number(row.received_qty)>0 && row.state === "pending" ? "Recebimento parcial" : labels[row.state])}</td><td><button id={`receive-open-${row.item_id}`} onClick={() => onOpen(row)}>{row.state === "pending" && writable ? "Receber mercadorias" : "Consultar"}</button></td></tr>)}
  </>;
}
