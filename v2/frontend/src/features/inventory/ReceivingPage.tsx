import {useEffect,useRef,useState} from "react";
import {Link,useSearchParams} from "react-router-dom";
import type {components} from "../../api/generated/schema";
import type {User} from "../auth/types";
import {canReadInventory,canWriteInventory} from "./inventoryPermissions";
import {useRead,number} from "./stockRead";
import type {StockLocation} from "./inventoryApi";
import "./receiving.css";
type Page=components['schemas']['ReceivingPage'];
type Row=components['schemas']['ReceivingRow'];
type Command=components['schemas']['ReceiveIn'];
type Result=components['schemas']['ReceiveResult'];
type Pending={body:Command;label:string;destination:string};
const labels={pending:"A receber",complete:"Recebido",blocked:"Bloqueado"};

export function ReceivingPage({user}:{user:User}){
 const [params,setParams]=useSearchParams(),allowed=canReadInventory(user),writable=canWriteInventory(user);
 const itemId=Number(params.get('item'))||0,q=params.get('q')||'',state=params.get('state')||'pending',offset=Number(params.get('offset'))||0;
 const queue=useRead<Page>(allowed?`/api/inventory/receiving?q=${encodeURIComponent(q)}&state=${state}&offset=${offset}`:null);
 const detail=useRead<Page>(allowed&&itemId?`/api/inventory/receiving?item_id=${itemId}&state=all`:null);
 const places=useRead<StockLocation[]>(allowed?'/api/inventory/locations':null);
 const row=detail.data?.rows[0],destinations=places.data?.filter(l=>l.active&&l.location_type==='DOMESTIC')||[];
 const key=`epic.receiving.pending:${user.id}`;
 const [pending,setPending]=useState<Pending|null>(()=>{try{return JSON.parse(sessionStorage.getItem(key)||'null');}catch{return null;}});
 const [quantity,setQuantity]=useState(''),[destination,setDestination]=useState('DOMESTIC-MAIN'),[error,setError]=useState(''),[busy,setBusy]=useState(false),[uncertain,setUncertain]=useState(!!pending),[result,setResult]=useState<Result|null>(null);
 const flight=useRef(false),heading=useRef<HTMLHeadingElement>(null),reviewHeading=useRef<HTMLHeadingElement>(null),lastItem=useRef(0),initialized=useRef(0);
 const qty=Number(quantity.replace(',','.')),invalid=!!row&&(!Number.isFinite(qty)||qty<=0||qty>Number(row.pending_qty)||!/^\d{1,14}([.,]\d{1,4})?$/.test(quantity));
 function patch(values:Record<string,string|null>){const next=new URLSearchParams(params);Object.entries(values).forEach(([k,v])=>v===null?next.delete(k):next.set(k,v));setParams(next);}
 function back(){if(busy||uncertain)return;lastItem.current=itemId;setPending(null);setError('');setResult(null);patch({item:null});}
 useEffect(()=>{if(row&&initialized.current!==row.item_id){initialized.current=row.item_id;setQuantity(row.pending_qty);setError('');heading.current?.focus();}},[row]);
 useEffect(()=>{if(!itemId){initialized.current=0;if(lastItem.current&&queue.data)(document.getElementById(`receive-open-${lastItem.current}`)||heading.current)?.focus();}},[itemId,queue.data]);
 useEffect(()=>{if(destinations.length&&!destinations.some(l=>l.code===destination))setDestination(destinations[0].code);},[places.data]);
 useEffect(()=>{const onKey=(e:KeyboardEvent)=>{if(e.key==='Escape'&&itemId&&!busy&&!uncertain){e.preventDefault();if(pending){setPending(null);requestAnimationFrame(()=>document.getElementById('receipt-quantity')?.focus());}else back();}};window.addEventListener('keydown',onKey);return()=>window.removeEventListener('keydown',onKey);});
 function review(r:Row){if(invalid||!r.unit||!destinations.some(l=>l.code===destination))return;setError('');setResult(null);setPending({body:{item_id:r.item_id,quantity:quantity.replace(',','.'),unit:r.unit,location_code:destination,request_key:crypto.randomUUID()},label:r.product_name||r.sku||'Produto',destination:destinations.find(l=>l.code===destination)!.name});requestAnimationFrame(()=>reviewHeading.current?.focus());}
 async function confirm(){if(!pending||flight.current)return;flight.current=true;setBusy(true);setError('');sessionStorage.setItem(key,JSON.stringify(pending));setUncertain(true);
  try{const response=await fetch('/api/inventory/receiving/confirm',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify(pending.body)});
   if(!response.ok){const p=await response.json().catch(()=>null);if(response.status<500){sessionStorage.removeItem(key);setUncertain(false);}throw new Error(typeof p?.message==='string'?p.message:'Não foi possível confirmar. Tente novamente.');}
   const value=await response.json() as Result;setResult(value);sessionStorage.removeItem(key);setPending(null);setUncertain(false);setQuantity(String(Math.max(0,Number(row?.pending_qty||0)-Number(value.quantity))));queue.retry();detail.retry();requestAnimationFrame(()=>document.getElementById('receipt-result')?.focus());
  }catch(e){setError(e instanceof TypeError?'Resposta não recebida. Tente confirmar novamente; a operação não será duplicada.':(e as Error).message);}finally{flight.current=false;setBusy(false);}
 }
 if(!allowed)return <section><h1>Recebimentos</h1><p role="alert">Seu acesso não permite consultar recebimentos.</p></section>;
 const loadingError=(r:{busy:boolean;error:string|null;retry:()=>void})=>r.busy?<p role="status">Carregando…</p>:r.error?<p role="alert">{r.error} <button onClick={r.retry}>Tentar novamente</button></p>:null;
 return <section className="receiving-page" data-testid="receiving-page">
  <header><h1 ref={heading} tabIndex={-1}>Recebimentos</h1><div>{itemId>0&&<button disabled={busy||uncertain} onClick={back}>← Voltar à fila</button>}<Link to="/inventory/positions">Estoque atual</Link></div></header>
  {error&&<p className="receiving-error" role="alert">{error}</p>}
  {result&&<div className="receiving-result" id="receipt-result" tabIndex={-1} role="status"><strong>Recebimento #{result.receipt_id} {result.status==='CONFIRMED'?'confirmado':'revertido'} · {number(result.quantity)} {row?.unit}</strong><span> {new Date(result.received_at!).toLocaleString('pt-BR')} · {result.location_code}</span><div><Link to={`/inventory/sku/${result.product_id}`}>Ver saldo</Link><Link to={`/inventory/movements?product_id=${result.product_id}`}>Ver histórico</Link></div></div>}
  {pending?<section className="receiving-review"><h2 ref={reviewHeading} tabIndex={-1}>Conferir recebimento</h2><p><strong>{pending.label}</strong></p><dl><div><dt>Quantidade</dt><dd>{number(pending.body.quantity)} {pending.body.unit}</dd></div><div><dt>Destino</dt><dd>{pending.destination}</dd></div></dl>{uncertain&&<p>Confirmação em verificação. Repetir usa a mesma operação.</p>}<div className="receiving-actions"><button className="receiving-primary" disabled={busy||!writable} onClick={()=>void confirm()}>{busy?'Confirmando…':'Confirmar recebimento'}</button><button disabled={busy||uncertain} onClick={()=>{setPending(null);setError('');requestAnimationFrame(()=>document.getElementById('receipt-quantity')?.focus());}}>Alterar</button></div></section>:itemId>0?<>
   {loadingError(detail)}{row&&<section className="receiving-detail"><p className="receiving-origin">{row.process_reference||row.process_code} · {row.release_reference||`Liberação ${row.nationalization_id}`}</p><h2>{row.product_name||row.sku||'Produto não vinculado'}</h2><p className="muted">{row.sku} · {row.unit||'Unidade não cadastrada'}</p><dl className="receiving-quantities"><div><dt>Liberado</dt><dd>{number(row.released_qty)} {row.unit}</dd></div><div><dt>Já recebido</dt><dd>{number(row.received_qty)} {row.unit}</dd></div><div><dt>Pendente</dt><dd data-testid="receiving-pending">{number(row.pending_qty)} {row.unit}</dd></div></dl>
    {row.state==='blocked'?<p role="alert">{row.block_reason}. Solicite a revisão à operação responsável.</p>:row.state==='complete'?<p role="status">Quantidade liberada totalmente recebida.</p>:writable?<form onSubmit={e=>{e.preventDefault();review(row);}}>
     <div className="receiving-fields"><label htmlFor="receipt-quantity">Quantidade ({row.unit})<input id="receipt-quantity" inputMode="decimal" value={quantity} aria-invalid={invalid} aria-describedby={invalid?'receiving-quantity-error':undefined} onChange={e=>setQuantity(e.target.value)}/></label><label>Destino<select aria-label="Destino" value={destination} onChange={e=>setDestination(e.target.value)}>{destinations.map(l=><option key={l.id} value={l.code}>{l.name}</option>)}</select></label></div>
     {invalid&&<p id="receiving-quantity-error" className="receiving-error">Informe uma quantidade maior que zero, até {number(row.pending_qty)} {row.unit}, com no máximo quatro casas decimais.</p>}{loadingError(places)}{places.data&&!destinations.length&&<p role="alert">Nenhuma localização doméstica ativa. Solicite a revisão do cadastro.</p>}
     <button className="receiving-primary" type="submit" disabled={invalid||!destinations.length}>Conferir recebimento</button>
    </form>:<p>Seu acesso permite consultar, mas não receber.</p>}
   </section>}{detail.data&&!row&&<p role="alert">Origem não encontrada.</p>}</>:<>
    <div className="receiving-filters"><label>Buscar<input aria-label="Buscar recebimento" placeholder="Produto, SKU ou operação" value={q} onChange={e=>patch({q:e.target.value,offset:null})}/></label><label>Situação<select aria-label="Situação do recebimento" value={state} onChange={e=>patch({state:e.target.value,offset:null})}><option value="pending">A receber</option><option value="complete">Recebidos</option><option value="blocked">Bloqueados</option><option value="all">Todos</option></select></label><button onClick={queue.retry}>Atualizar</button></div>
    {loadingError(queue)}{queue.data&&<><p className="muted">{queue.data.total} {queue.data.total===1?'item':'itens'}</p>{queue.data.rows.length?<div className="experience-table-wrap"><table className="experience-table"><thead><tr><th>Produto / origem</th><th>Unidade</th><th className="numeric">Liberado</th><th className="numeric">Recebido</th><th className="numeric">Pendente</th><th>Situação</th><th><span className="sr-only">Ação</span></th></tr></thead><tbody>{queue.data.rows.map(r=><tr key={r.item_id}><td><strong>{r.product_name||'Produto não vinculado'}</strong><small>{r.sku} · {r.process_reference||r.process_code} · {r.release_reference}</small></td><td>{r.unit||'Não cadastrada'}</td><td className="numeric">{number(r.released_qty)}</td><td className="numeric">{number(r.received_qty)}</td><td className="numeric"><strong>{number(r.pending_qty)}</strong></td><td>{r.block_reason||labels[r.state]}</td><td><button id={`receive-open-${r.item_id}`} onClick={()=>{setResult(null);patch({item:String(r.item_id)});}}>{r.state==='pending'&&writable?'Receber':'Consultar'}</button></td></tr>)}</tbody></table></div>:<p>Nenhum recebimento neste filtro.</p>}
    {queue.data.total>25&&<div className="receiving-actions"><button disabled={!offset} onClick={()=>patch({offset:String(Math.max(0,offset-25))})}>Anterior</button><span>{offset+1}–{Math.min(offset+25,queue.data.total)} de {queue.data.total}</span><button disabled={offset+25>=queue.data.total} onClick={()=>patch({offset:String(offset+25)})}>Próxima</button></div>}</>}
   </>}
 </section>;
}
