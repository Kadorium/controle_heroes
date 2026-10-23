import { useEffect, useState } from "react";
export const regimes = { DOMESTIC:"Disponível", BONDED:"Entreposto", QUARANTINE:"Quarentena" } as const;
export type Regime = keyof typeof regimes;
export type StockRow = { product_id:number; sku:string; name:string; unit:string | null; quantities:Record<Regime,string>; balances:{location_id:number; code:string; name:string; regime:Regime; qty:string}[] };
export type StockPosition = { rows:StockRow[]; locations:{id:number;name:string;regime:Regime}[]; total:number; offset:number; limit:number; totals:{unit:string|null; quantities:Record<Regime,string|null>; sku_count:number; quantity_state:string}[]; generated_at:string };
export type CostProduct = { product_id:number; qty:string; unit_brl:string|null; total_brl:string|null };
export type CostVersion = { id:number; number:number; kind:string; status:string; partial_coverage:boolean; product:CostProduct|null; invoices:{id:number; number:string}[] };
export type CostSource = {case_id:number; process_id:number; code:string; reference:string|null; purchases:{id:number;code:string}[]; current_published_id:number|null; versions:CostVersion[]};
export type CostSources = {rows:CostSource[]; total:number; limit:number; offset:number};
export type ProductCost = {product_id:number; case_id:number; version_id:number; number:number; kind:string; status:string; current_published_id:number|null; partial_coverage:boolean; product:CostProduct|null; fx:{kind?:string; documentary_rate?:string; statuses?:string[]}; coverage:{coverage?:string}; components:{id:number; type:string; included:boolean; product_brl:string|null; process_brl:string|null; source_kind:string; source_id:number; documents:{id:number; name:string; mime_type:string|null}[]; document_state:string}[]};
export const number = (value:string|number|null|undefined) => value == null ? "Não informado" : new Intl.NumberFormat("pt-BR",{maximumFractionDigits:4}).format(Number(value));
export const money = (value:string|null|undefined) => value == null ? "Não informado" : new Intl.NumberFormat("pt-BR",{style:"currency",currency:"BRL"}).format(Number(value));
export const kindLabel:Record<string,string> = {ESTIMATED:"Estimado", REVISED:"Revisado", REALIZED:"Realizado"};
export const statusLabel:Record<string,string> = {DRAFT:"Rascunho",PUBLISHED:"Publicado",SUPERSEDED:"Substituído",CANCELLED:"Cancelado"};
export function useRead<T>(url:string|null) {
  const [retry,setRetry] = useState(0), [state,setState] = useState<{url:string|null; data:T|null; error:string|null; busy:boolean}>({url:null,data:null,error:null,busy:false});
  useEffect(() => {
    if (!url) { setState({url,data:null,error:null,busy:false}); return; }
    const controller = new AbortController(); setState({url,data:null,error:null,busy:true});
    void fetch(url,{credentials:"include",signal:controller.signal}).then(async r => {
      if (!r.ok) {
        const problem=await r.json().catch(()=>null);
        throw new Error(r.status===403 ? "Seu acesso não permite consultar esta informação." : r.status===404 ? "Registro não encontrado." : r.status===422 && typeof problem?.message==="string" ? problem.message : "Não foi possível carregar esta informação.");
      }
      return await r.json() as T;
    }).then(data => { if(!controller.signal.aborted) setState({url,data,error:null,busy:false}); })
      .catch(e => {if(!controller.signal.aborted) setState({url,data:null,error:String(e.message),busy:false});});
    return () => controller.abort();
  },[url,retry]);
  return {...(state.url===url ? state : {data:null,error:null,busy:!!url}), retry:()=>setRetry(v=>v+1)};
}
