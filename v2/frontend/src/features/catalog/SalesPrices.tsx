import {useRef,useState} from "react";
import {Link} from "react-router-dom";
import type {User} from "../auth/types";
import {money,useRead} from "../inventory/stockRead";
import {stockWrite} from "../inventory/stockExplorerModel";
import {formatDateTime} from "../dashboard/localDateTime";
import "./salesPrices.css";
export type Price={id:number;list_id:number;amount:string;unit:string;valid_from:string;valid_to:string|null;reason:string;cancelled:boolean;revision_token:string};
export type PriceList={id:number;name:string;currency:string;channel:string;nature:string};
const dateLabel=(s:string)=>s.split("-").reverse().join("/");
export const priceToday=()=>new Intl.DateTimeFormat("en-CA",{timeZone:"America/Sao_Paulo"}).format(new Date());
function History({id}:{id:number}){
  const read=useRead<{action:string;at:string;details:null|{reason?:string;before?:Price;after?:Price}}[]>(`/api/catalog/sales-prices/${id}/history`);
  return <div className="price-history" aria-label="Histórico do preço">{read.busy&&<p role="status">Carregando histórico…</p>}{read.error&&<p role="alert">{read.error} <button onClick={read.retry}>Tentar novamente</button></p>}{read.data?.map((h,i)=><p key={i}><strong>{{create:"Cadastrado",replace:"Substituído",close:"Vigência encerrada"}[h.action]||h.action}</strong> · {formatDateTime(h.at)}{h.details?.reason&&<> · {h.details.reason}</>}{h.details?.before&&<> · Antes: {money(h.details.before.amount)}, {dateLabel(h.details.before.valid_from)} a {h.details.before.valid_to?dateLabel(h.details.before.valid_to):"sem término"}. Depois: {h.details.after?.cancelled?"substituído na mesma data":`até ${h.details?.after?.valid_to?dateLabel(h.details.after.valid_to):"sem término"}`}.</>}</p>)}</div>;
}
export function SalesPrices({productId,unit,user}:{productId:number;unit:string|null;user:User}){
  const can=(p:string)=>user.role==="admin"||user.permissions.includes(p),allowed=can("catalog:prices_read");
  const read=useRead<Price[]>(allowed?`/api/catalog/sales-prices?product_id=${productId}`:null),lists=useRead<PriceList[]>(allowed?"/api/catalog/price-lists":null);
  const [mode,setMode]=useState<"create"|"replace"|"close"|null>(null),[selected,setSelected]=useState<Price|null>(null),[history,setHistory]=useState<number|null>(null);
  const [amount,setAmount]=useState(""),[from,setFrom]=useState(priceToday()),[to,setTo]=useState(""),[reason,setReason]=useState(""),[list,setList]=useState(0),[busy,setBusy]=useState(false),[message,setMessage]=useState(""),[error,setError]=useState("");
  const requestKey=useRef(crypto.randomUUID()),trigger=useRef<HTMLElement|null>(null);
  if(!allowed)return null;
  function close(){setMode(null);setHistory(null);requestAnimationFrame(()=>{if(trigger.current?.isConnected)trigger.current.focus();else document.getElementById('add-sale-price')?.focus();});}
  function open(next:"create"|"replace"|"close",p:Price|null,event:React.MouseEvent<HTMLButtonElement>){trigger.current=event.currentTarget;setSelected(p);setMode(next);setHistory(null);setError("");setMessage("");setAmount(p?.amount||"");setFrom(p&&p.valid_from>priceToday()?p.valid_from:priceToday());setTo(next==="close"?(p&&p.valid_from>priceToday()?p.valid_from:priceToday()):"");setReason("");requestKey.current=crypto.randomUUID();}
  async function save(){
    if(busy)return;setError("");
    if(!reason.trim()){setError("Informe o motivo.");return;}
    if(mode!=="close"&&to&&to<from){setError("O fim deve ser igual ou posterior ao início.");return;}
    setBusy(true);
    try{
      if(mode==="create")await stockWrite("/api/catalog/sales-prices",{product_id:productId,list_id:list||lists.data?.[0]?.id,amount,unit,valid_from:from,valid_to:to||null,reason,request_key:requestKey.current});
      else await stockWrite(`/api/catalog/sales-prices/${selected!.id}/change`,{action:mode,expected_token:selected!.revision_token,amount:mode==="replace"?amount:null,unit,valid_from:mode==="replace"?from:null,valid_to:to||null,reason,request_key:requestKey.current});
      read.retry();close();setMessage(mode==="close"?"Vigência encerrada. Histórico preservado.":mode==="replace"?"Preço substituído. Histórico preservado.":"Preço registrado.");
    }catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  const currentList=lists.data?.find(l=>l.id===(selected?.list_id||list||lists.data?.[0]?.id));
  return <section className="experience-cost sales-prices" data-testid="sales-prices" onKeyDown={e=>{if(e.key==="Escape"&&!busy){e.stopPropagation();close();}}}>
    <div className="experience-cost-header"><h2>Preços de venda</h2>{can("catalog:prices_write")&&<div className="price-actions"><Link to="/catalog/prices/import">Importar CSV</Link><button id="add-sale-price" onClick={e=>open("create",null,e)}>Novo preço</button></div>}</div>
    {message&&<p role="status">{message}</p>}{read.error&&<p role="alert">{read.error} <button onClick={read.retry}>Tentar novamente</button></p>}{read.busy&&<p role="status">Carregando preços…</p>}
    {mode&&<form className="price-form" onSubmit={e=>{e.preventDefault();void save();}}>
      <h3>{mode==="create"?"Novo preço":mode==="replace"?"Substituir preço":"Encerrar vigência"}</h3>
      <div className="experience-toolbar">
        {mode==="create"?<label>Tabela<select aria-label="Tabela do preço" value={list||lists.data?.[0]?.id||""} onChange={e=>setList(Number(e.target.value))}>{lists.data?.map(l=><option key={l.id} value={l.id}>{l.name} · {l.currency} · {l.channel}</option>)}</select></label>:<span>{currentList?.name} · {currentList?.channel} · {currentList?.currency}</span>}
        {mode!=="close"&&<><label>Preço em reais<input autoFocus aria-label="Preço em reais" type="number" min="0.0001" step="0.0001" required value={amount} onChange={e=>setAmount(e.target.value)}/></label><label>Válido de<input aria-label="Preço válido de" type="date" min={mode==="replace"?priceToday():undefined} required value={from} onChange={e=>setFrom(e.target.value)}/></label></>}
        <label>{mode==="close"?"Último dia válido":"Válido até"}<input autoFocus={mode==="close"} aria-label="Preço válido até" type="date" required={mode==="close"} value={to} onChange={e=>setTo(e.target.value)}/></label>
        <label>Motivo<input aria-label="Motivo do preço" required maxLength={512} value={reason} onChange={e=>setReason(e.target.value)}/></label>
      </div>
      <p className="muted">{unit||"Cadastre a unidade do produto"} · preço bruto{mode==="replace"?" · o preço anterior permanece no histórico":mode==="close"?" · o preço continua válido até o dia informado":""}</p>
      {error&&<p role="alert">{error}</p>}
      <div className="price-actions"><button type="submit" disabled={busy||!unit||!lists.data?.length}>{busy?"Salvando…":mode==="create"?"Registrar preço":mode==="replace"?"Confirmar substituição":"Confirmar encerramento"}</button><button type="button" disabled={busy} onClick={close}>Cancelar</button></div>
    </form>}
    {read.data?.length?<div className="experience-table-wrap"><table className="experience-table"><thead><tr><th>Tabela / canal</th><th>Preço / unidade</th><th>Vigência</th><th>Situação</th><th>Ações</th></tr></thead><tbody>{read.data.map(p=>{
      const ended=!!p.valid_to&&p.valid_to<priceToday(),state=p.cancelled?"Substituído":ended?"Encerrado":p.valid_from>priceToday()?"Futuro":"Vigente",table=lists.data?.find(l=>l.id===p.list_id);
      return <tr key={p.id} data-price-id={p.id}><td>{table?.name||p.list_id}<small>{table?.channel} · {table?.currency} · bruto</small></td><td>{money(p.amount)} / {p.unit}</td><td>{dateLabel(p.valid_from)} → {p.valid_to?dateLabel(p.valid_to):"Sem término"}</td><td>{state}</td><td><div className="price-actions">{can("catalog:prices_write")&&!ended&&!p.cancelled&&<><button onClick={e=>open("replace",p,e)}>Substituir</button><button onClick={e=>open("close",p,e)}>Encerrar</button></>}<button aria-expanded={history===p.id} onClick={e=>{trigger.current=e.currentTarget;setMode(null);setHistory(history===p.id?null:p.id);}}>Histórico</button></div>{history===p.id&&<><p>{p.reason}</p><History id={p.id}/><button onClick={close}>Fechar histórico</button></>}</td></tr>;
    })}</tbody></table></div>:!read.busy&&<p className="muted">Sem preço cadastrado.</p>}
  </section>;
}
